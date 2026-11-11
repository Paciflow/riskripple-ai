import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import * as sns from "aws-cdk-lib/aws-sns";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as path from "path";
import { Construct } from "constructs";

export interface WorkflowStackProps extends cdk.StackProps {
  dataBucket: s3.Bucket;
  analysesTable: dynamodb.Table;
  eventsTable: dynamodb.Table;
  portfoliosTable: dynamodb.Table;
  auditTable: dynamodb.Table;
}

/**
 * Asynchronous investigation workflow (master spec section 15). The spec's 13
 * conceptual states (ValidateAnalysisRequest ... NotifyCompletion) are currently
 * implemented as sub-steps INSIDE one Lambda
 * (backend/src/riskripple/workflows/local_orchestrator.py), not as 13 separate Step
 * Functions states. That collapse is deliberate, not a shortcut taken to pad out the
 * state count: the spec itself says to prioritize reliable tool execution over the
 * number of states/agents, and splitting each conceptual step into its own Lambda
 * task before the live Bedrock agent path is verified (see
 * docs/KNOWN_LIMITATIONS.md) would add retry/catch surface area for behavior that
 * hasn't been proven to work yet. Once bedrock:InvokeModel access is confirmed on
 * the hackathon account, decompose RunInvestigationTask into per-agent tasks with
 * their own retry policies -- the state names below are kept aligned with the spec's
 * section 15 list so that decomposition is a refactor, not a redesign.
 */
export class WorkflowStack extends cdk.Stack {
  public readonly stateMachine: sfn.StateMachine;

  constructor(scope: Construct, id: string, props: WorkflowStackProps) {
    super(scope, id, props);

    const completionTopic = new sns.Topic(this, "AnalysisCompletionTopic", {
      displayName: "RiskRipple analysis completion notifications",
    });

    const runInvestigationFn = new lambda.DockerImageFunction(this, "RunInvestigationFn", {
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, "../../.."), {
        file: "backend/Dockerfile.lambda",
        cmd: ["riskripple.api.handlers.analyses.handler"],
      }),
      timeout: cdk.Duration.minutes(5),
      memorySize: 2048,
      environment: {
        RISKRIPPLE_DATA_BUCKET: props.dataBucket.bucketName,
        ANALYSES_TABLE: props.analysesTable.tableName,
        EVENTS_TABLE: props.eventsTable.tableName,
        PORTFOLIOS_TABLE: props.portfoliosTable.tableName,
        AUDIT_TABLE: props.auditTable.tableName,
        RISKRIPPLE_USE_DYNAMO: "1",
      },
    });
    props.dataBucket.grantReadWrite(runInvestigationFn);
    props.analysesTable.grantReadWriteData(runInvestigationFn);
    props.eventsTable.grantReadWriteData(runInvestigationFn);
    props.portfoliosTable.grantReadWriteData(runInvestigationFn);
    props.auditTable.grantReadWriteData(runInvestigationFn);

    // ValidateAnalysisRequest .. ValidateCitations .. PersistResults are performed
    // inside this single task today (see class docstring above).
    const runInvestigation = new tasks.LambdaInvoke(this, "RunInvestigationTask", {
      lambdaFunction: runInvestigationFn,
      outputPath: "$.Payload",
    }).addRetry({
      errors: ["States.TaskFailed"],
      interval: cdk.Duration.seconds(2),
      maxAttempts: 2,
      backoffRate: 2.0,
    });

    const notifyCompletion = new tasks.SnsPublish(this, "NotifyCompletion", {
      topic: completionTopic,
      message: sfn.TaskInput.fromJsonPathAt("$"),
    });

    const notifyFailure = new tasks.SnsPublish(this, "NotifyFailure", {
      topic: completionTopic,
      message: sfn.TaskInput.fromObject({
        status: "failed",
        error: sfn.JsonPath.stringAt("$.Cause"),
      }),
    });

    const definition = runInvestigation
      .addCatch(notifyFailure, { resultPath: "$.error" })
      .next(notifyCompletion);

    this.stateMachine = new sfn.StateMachine(this, "InvestigationStateMachine", {
      stateMachineName: "riskripple-investigation",
      definitionBody: sfn.DefinitionBody.fromChainable(definition),
      timeout: cdk.Duration.minutes(10),
      tracingEnabled: true,
    });

    new cdk.CfnOutput(this, "StateMachineArn", { value: this.stateMachine.stateMachineArn });
  }
}

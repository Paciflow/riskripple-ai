import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as path from "path";
import { Construct } from "constructs";

export interface ApiStackProps extends cdk.StackProps {
  dataBucket: s3.Bucket;
  analysesTable: dynamodb.Table;
  eventsTable: dynamodb.Table;
  portfoliosTable: dynamodb.Table;
  auditTable: dynamodb.Table;
}

/**
 * API layer: a container-image Lambda (see backend/Dockerfile.lambda) shared across
 * handlers, fronted by API Gateway. A single image is used for all handlers here
 * (small endpoint count, same heavy dependency set) rather than one image per
 * handler, to avoid rebuilding pandas/numpy/scipy/networkx/strands-agents N times.
 */
export class ApiStack extends cdk.Stack {
  public readonly api: apigateway.RestApi;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    // Build context is the repo root (not backend/) -- see backend/Dockerfile.lambda
    // for why the frozen demo data snapshot needs to be in the build context too.
    const repoRoot = path.join(__dirname, "../../..");

    const sharedEnv = {
      RISKRIPPLE_DATA_BUCKET: props.dataBucket.bucketName,
      ANALYSES_TABLE: props.analysesTable.tableName,
      EVENTS_TABLE: props.eventsTable.tableName,
      PORTFOLIOS_TABLE: props.portfoliosTable.tableName,
      AUDIT_TABLE: props.auditTable.tableName,
      RISKRIPPLE_USE_DYNAMO: "1",
    };

    const makeHandler = (id: string, cmd: string, timeoutSeconds = 30, memoryMb = 1024) => {
      const fn = new lambda.DockerImageFunction(this, id, {
        code: lambda.DockerImageCode.fromImageAsset(repoRoot, {
          file: "backend/Dockerfile.lambda",
          cmd: [cmd],
        }),
        timeout: cdk.Duration.seconds(timeoutSeconds),
        memorySize: memoryMb,
        environment: sharedEnv,
      });
      props.dataBucket.grantReadWrite(fn);
      props.analysesTable.grantReadWriteData(fn);
      props.eventsTable.grantReadWriteData(fn);
      props.portfoliosTable.grantReadWriteData(fn);
      props.auditTable.grantReadWriteData(fn);
      return fn;
    };

    const healthFn = makeHandler("HealthFn", "riskripple.api.handlers.health.handler", 10, 256);
    // Heavier: loads pandas/scipy and runs the full orchestrator synchronously
    // (see backend/src/riskripple/api/handlers/analyses.py for why this is sync
    // for the demo instead of a Step Functions kickoff).
    const analysesFn = makeHandler("AnalysesFn", "riskripple.api.handlers.analyses.handler", 60, 2048);

    this.api = new apigateway.RestApi(this, "RiskRippleApi", {
      restApiName: "riskripple-api",
      deployOptions: { stageName: "prod", tracingEnabled: true },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
      },
    });

    this.api.root.addResource("health").addMethod("GET", new apigateway.LambdaIntegration(healthFn));

    const analyses = this.api.root.addResource("api").addResource("analyses");
    analyses.addMethod("POST", new apigateway.LambdaIntegration(analysesFn));
    analyses.addResource("{analysis_id}").addMethod("GET", new apigateway.LambdaIntegration(analysesFn));

    new cdk.CfnOutput(this, "ApiUrl", { value: this.api.url });
  }
}

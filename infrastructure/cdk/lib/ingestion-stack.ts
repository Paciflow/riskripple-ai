import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as path from "path";
import { Construct } from "constructs";

export interface IngestionStackProps extends cdk.StackProps {
  dataBucket: s3.Bucket;
}

/**
 * Scheduled ingestion (master spec section 7): refreshes OFAC/GAC/Federal
 * Register/FRED data on a daily schedule. One Lambda, several EventBridge rules --
 * the adapters are cheap, low-volume calls (see docs/DATA_SOURCES.md for per-source
 * rate-limit notes), so a single daily run per source is deliberately conservative.
 */
export class IngestionStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: IngestionStackProps) {
    super(scope, id, props);

    const ingestFn = new lambda.DockerImageFunction(this, "IngestFn", {
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, "../../.."), {
        file: "backend/Dockerfile.lambda",
        cmd: ["riskripple.api.handlers.ingest.handler"],
      }),
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024,
      environment: { RISKRIPPLE_DATA_BUCKET: props.dataBucket.bucketName },
    });
    props.dataBucket.grantReadWrite(ingestFn);

    new events.Rule(this, "DailyIngestionRule", {
      schedule: events.Schedule.rate(cdk.Duration.hours(24)),
      targets: [new targets.LambdaFunction(ingestFn)],
      description: "Daily refresh of OFAC/GAC/Federal Register/FRED source snapshots",
    });
  }
}

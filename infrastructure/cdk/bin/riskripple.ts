#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { StorageStack } from "../lib/storage-stack";
import { ApiStack } from "../lib/api-stack";
import { IngestionStack } from "../lib/ingestion-stack";
import { WorkflowStack } from "../lib/workflow-stack";

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || "us-east-2",
};

const storage = new StorageStack(app, "RiskRipple-Storage", { env });

new ApiStack(app, "RiskRipple-Api", {
  env,
  dataBucket: storage.dataBucket,
  analysesTable: storage.analysesTable,
  eventsTable: storage.eventsTable,
  portfoliosTable: storage.portfoliosTable,
  auditTable: storage.auditTable,
});

new IngestionStack(app, "RiskRipple-Ingestion", {
  env,
  dataBucket: storage.dataBucket,
});

new WorkflowStack(app, "RiskRipple-Workflow", {
  env,
  dataBucket: storage.dataBucket,
  analysesTable: storage.analysesTable,
  eventsTable: storage.eventsTable,
  portfoliosTable: storage.portfoliosTable,
  auditTable: storage.auditTable,
});

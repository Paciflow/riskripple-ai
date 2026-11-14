import * as cdk from "aws-cdk-lib";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { Construct } from "constructs";

/**
 * Storage foundation (master spec sections 7 and 14): the S3 data lake prefixes and
 * the DynamoDB tables for structured application state. Large raw documents, report
 * files, and financial datasets live in S3; DynamoDB holds the structured entities
 * that reference them by key.
 */
export class StorageStack extends cdk.Stack {
  public readonly dataBucket: s3.Bucket;
  public readonly analysesTable: dynamodb.Table;
  public readonly eventsTable: dynamodb.Table;
  public readonly portfoliosTable: dynamodb.Table;
  public readonly auditTable: dynamodb.Table;
  public readonly alertsTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Deployment-generated bucket name (account/region suffix) rather than assuming a
    // globally unique fixed name is available -- see master spec section 7.
    this.dataBucket = new s3.Bucket(this, "DataLakeBucket", {
      bucketName: `riskripple-data-${this.account}-${this.region}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          id: "expire-noncurrent-versions",
          noncurrentVersionExpiration: cdk.Duration.days(90),
        },
      ],
    });

    // Prefixes are created implicitly on first write; CfnOutput below documents the
    // expected layout for ingestion Lambdas rather than pre-creating empty "folders".
    new cdk.CfnOutput(this, "DataLakePrefixes", {
      value: [
        "raw/regulatory/", "raw/filings/", "raw/market/",
        "processed/regulatory/", "processed/market/", "processed/relationships/",
        "rag/documents/", "analysis/", "reports/",
      ].join(", "),
    });

    this.portfoliosTable = new dynamodb.Table(this, "PortfoliosTable", {
      tableName: "riskripple-portfolios",
      partitionKey: { name: "portfolio_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      pointInTimeRecovery: true,
    });

    this.eventsTable = new dynamodb.Table(this, "RegulatoryEventsTable", {
      tableName: "riskripple-regulatory-events",
      partitionKey: { name: "event_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      pointInTimeRecovery: true,
      timeToLiveAttribute: "ttl",
    });
    this.eventsTable.addGlobalSecondaryIndex({
      indexName: "by-jurisdiction",
      partitionKey: { name: "jurisdiction", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "publication_date", type: dynamodb.AttributeType.STRING },
    });

    this.analysesTable = new dynamodb.Table(this, "AnalysesTable", {
      tableName: "riskripple-analyses",
      partitionKey: { name: "analysis_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      pointInTimeRecovery: true,
    });
    this.analysesTable.addGlobalSecondaryIndex({
      indexName: "by-portfolio",
      partitionKey: { name: "portfolio_id", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "created_at", type: dynamodb.AttributeType.STRING },
    });

    this.auditTable = new dynamodb.Table(this, "AuditEventsTable", {
      tableName: "riskripple-audit-events",
      partitionKey: { name: "audit_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      timeToLiveAttribute: "ttl",
    });
    this.auditTable.addGlobalSecondaryIndex({
      indexName: "by-analysis",
      partitionKey: { name: "analysis_id", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "timestamp", type: dynamodb.AttributeType.STRING },
    });

    // User-facing alerts (riskripple.alerts.pipeline): a new regulatory document
    // judged relevant to a tracked portfolio via the real exposure graph, with the
    // auto-triggered investigation it produced. Distinct from RegulatoryEventsTable
    // (which is the raw "have we seen this document" diffing ledger, keyed by the
    // document itself) and from AuditEventsTable (internal pipeline execution log).
    this.alertsTable = new dynamodb.Table(this, "AlertsTable", {
      tableName: "riskripple-alerts",
      partitionKey: { name: "alert_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      pointInTimeRecovery: true,
    });
    this.alertsTable.addGlobalSecondaryIndex({
      indexName: "by-status",
      partitionKey: { name: "status", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "detected_at", type: dynamodb.AttributeType.STRING },
    });
  }
}

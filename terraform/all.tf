//module "acm_pca" {
//  source = "./acm-pca"
//}
//
//module "cloudwatch_resource_policy" {
//  source = "./cloudwatch-resource-policy"
//}
//
//module "ebs" {
//  source = "./ebs-snapshot"
//}
//
//module "ecr" {
//  source = "./ecr-repository"
//}
//
//module "efs" {
//  source = "./efs-file-system"
//}
//
////module "elasticsearch_domain" {
////  source = "./elasticsearch-domain"
////}
//
//module "glacier" {
//  source = "./glacier-vault"
//}
//
//module "iam_role" {
//  source = "./iam-role"
//}
//
//module "lambda_function" {
//  source = "./lambda-function"
//}
//
//module "lambda_layer" {
//  source = "./lambda-layer"
//}
//
//module "rds_snapshot" {
//  source = "./rds-snapshot"
//}
//
//module "s3_bucket" {
//  source = "./s3-bucket"
//}
//
//
//module "secrets_manager" {
//  source = "./secrets-manager"
//}
//
//module "ses_identity" {
//  source      = "./ses-domain-identity"
//}
//
//module "sns_topic" {
//  source = "./sns-topic"
//}
//
//module "sqs_queue" {
//  source = "./sqs-queue"
//}

module "ec2_ami" {
  source = "./ec2-ami"
}

output "names" {
  value = module.ec2_ami.ami_id
}

/*
ElasticSearch Domain: ${module.elasticsearch_domain.name}
*/

//output "names" {
//  value = <<README
//ACM Private Certificate Authority (ACM PCA): ${module.acm_pca.arn}
//ECR Registry: ${module.ecr.name}
//EBS Volume: ${module.ebs.id}
//EFS File System: ${module.efs.id}
//IAM Role: ${module.iam_role.name}
//Lambda Function: ${module.lambda_function.name}
//Lambda Layer: ${module.lambda_layer.name}
//RDS Snapshot: ${module.rds_snapshot.snapshot_identifier}
//S3 Bucket: ${module.s3_bucket.name}
//Secrets Manager: ${module.secrets_manager.name}
//SES Identity: ${module.ses_identity.name}
//SNS Topic: ${module.sns_topic.name}
//SQS Queue: ${module.sqs_queue.name}
//README
//}

// For the ACM Private Certificate Authority, you will need to access the AWS console after it is created. See the tutorial for more instructions.

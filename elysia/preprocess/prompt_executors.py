import ast

import dspy

# Prompt Templates
from elysia.preprocess.prompt_templates import (
    CollectionSummariserPrompt,
    DataMappingPrompt,
    ReturnTypePrompt,
)


class CollectionSummariserExecutor(dspy.Module):
    def __init__(self):
        super().__init__()
        self.collection_summariser_prompt = dspy.ChainOfThought(
            CollectionSummariserPrompt
        )

    def forward(self, data: list[dict], data_fields: list[str], lm: dspy.LM) -> dict:
        prediction = self.collection_summariser_prompt(
            data=data, data_fields=data_fields, lm=lm
        )
        summary_concat = ""
        for sentence in [
            prediction.sentence1,
            prediction.sentence2,
            prediction.sentence3,
            prediction.sentence4,
            prediction.sentence5,
        ]:
            if (
                sentence.endswith(".")
                or sentence.endswith("?")
                or sentence.endswith("!")
                or sentence.endswith("\n")
            ):
                summary_concat += f"{sentence} "
            else:
                summary_concat += f"{sentence}."
        return summary_concat


class ReturnTypeExecutor(dspy.Module):
    def __init__(self):
        super().__init__()
        self.return_type_prompt = dspy.ChainOfThought(ReturnTypePrompt)

    def forward(
        self,
        collection_summary: str,
        data_fields: dict,
        example_objects: list[dict],
        possible_return_types: list[str],
        lm: dspy.LM,
    ):
        prediction = self.return_type_prompt(
            collection_summary=collection_summary,
            data_fields=data_fields,
            example_objects=example_objects,
            possible_return_types=possible_return_types,
            lm=lm,
        )
        return_types = prediction.return_types

        return return_types


class DataMappingExecutor(dspy.Module):
    def __init__(self):
        super().__init__()
        self.data_mapping_prompt = dspy.ChainOfThought(DataMappingPrompt)

    def forward(
        self,
        input_data_fields: list,
        output_data_fields: list,
        input_data_types: dict,
        collection_information: dict,
        example_objects: list[dict],
        lm: dspy.LM,
    ):
        prediction = self.data_mapping_prompt(
            input_data_fields=input_data_fields,
            output_data_fields=output_data_fields,
            input_data_types=input_data_types,
            collection_information=collection_information,
            example_objects=example_objects,
            lm=lm,
        )

        return prediction.field_mapping, prediction, ""

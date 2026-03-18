import os
from typing import Any

from owlready2 import (
    DataPropertyClass,
    ObjectPropertyClass,
    PropertyClass,
    datetime,
    get_ontology,
)
from owlready2.class_construct import And, Or, Restriction
from owlready2.entity import ThingClass
from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
import segittur_commons.app.entities.graphql_models as models

from segittur_commons.config.global_context import DEFAULT_LLM_LANGUAGE_ID


class OWLParser:

    _DATATYPE_MAP = {
        str: "str",
        int: "int",
        float: "float",
        bool: "bool",
        datetime.date: "date",
        datetime.datetime: "datetime",
    }

    def __init__(self, uri: str, main_bussines_classes: list[str]):
        self.ontology = get_ontology(uri).load()
        self.main_bussines_classes = main_bussines_classes
        self.max_depth = 4
        # Pre-cache all properties for efficiency.
        self._all_ontology_properties: list[PropertyClass] = list(
            self.ontology.object_properties()
        ) + list(self.ontology.data_properties())
        self.presentation_order_category_prop = self.ontology.search_one(
            iri="*presentationOrderCategory"
        )

    @property
    def classes(self) -> list:
        return list(self.ontology.classes())

    def get_ontology_main_classes(self) -> list:
        return [
            ontology_class
            for ontology_class in self.classes
            if (
                len(self.ontology.get_children_of(ontology_class)) > 0
                and ontology_class.is_a[0].name == "Thing"
                and ontology_class.namespace.name == self.ontology.name
            )
        ]

    def get_bussines_main_classes(self) -> list:
        return [
            ontology_class
            for ontology_class in self.classes
            if ontology_class.name in self.main_bussines_classes
        ]

    def get_classes_description(self, classes: list) -> dict[str, str]:
        return {
            cl.name: cl.comment.get_lang(DEFAULT_LLM_LANGUAGE_ID).first() if cl.comment else ""
            for cl in classes
        }

    def get_classes_names(self, classes: list[ThingClass]) -> list[str]:
        return [ontology_class.name for ontology_class in classes]

    def get_classes_from_names(
        self, names: list[str], classes: list[ThingClass]
    ) -> list[ThingClass]:
        return [ontology_class for ontology_class in classes if ontology_class.name in names]

    def get_all_properties_for_classes(
        self, classes: list[ThingClass]
    ) -> dict[str, set[PropertyClass]]:
        """
        Retrieves all properties for a list of ontology classes, returning a
        dictionary that maps each class name to its corresponding set of properties.

        This method acts as a convenient wrapper around `get_all_properties_for_class`.

        Args:
            classes: A list of owlready2 classes (e.g., [onto.Hotel, onto.Restaurant]).

        Returns:
            A dictionary where keys are the string names of the input classes and
            values are sets of unique owlready2 property objects.
        """
        results = {}
        for cls in classes:
            # Using cls.name as the key for better readability and serialization.
            schema = self.get_all_properties_for_class(cls)
            results[cls.name] = {"properties": schema["properties"], "$defs": schema['$defs']}
        return results

    def get_subclasses(self, ontology_class: ThingClass) -> set[ThingClass] | Any:
        return ThingClass.descendants(ontology_class, include_self=False)

    def get_parents(self, ontology_class: ThingClass) -> set[ThingClass] | Any:
        return ThingClass.ancestors(ontology_class)

    def get_all_subclasses(self, original_classes: list) -> set:
        all_subclasses: set[ThingClass] = set()
        for original_class in original_classes:
            all_subclasses.update(self.get_subclasses(original_class))
        return all_subclasses

    def classes_properties_primitives_for_schema_dict(
        self, properties_classes_dict: dict[str, list[PropertyClass]]
    ) -> dict[str, dict]:
        results = {}
        for class_name, properties in properties_classes_dict.items():
            # Using cls.name as the key for better readability and serialization.
            results[class_name] = self.properties_to_primitives_schema_dict(properties)
        return results

    def properties_to_primitives_schema_dict(self, properties: list[PropertyClass]) -> dict:
        """
        Recursively builds a dictionary representing the schema of properties.
        """
        return self._properties_to_primitives_recursive(properties, set())

    def _properties_to_primitives_recursive(
        self,
        properties: list[PropertyClass],
        visited_classes: set[ThingClass],
        is_top_level: bool = True,
    ) -> dict:
        """
        Internal helper for recursively generating the property schema.

        Args:
            properties: The list of properties to process at the current level.
            visited_classes: A set of classes already visited in the current recursion
                             path to prevent infinite loops.
            is_top_level: A boolean to indicate if the properties are at the root
                          level of the schema, used to handle acknowledgement properties.

        Returns:
            A dictionary representing the schema for the given properties.
        """
        schema: dict[str, dict | str] = {}
        sorted_properties = sorted(properties, key=lambda p: p.name)

        for prop in sorted_properties:
            if not hasattr(prop, "range") or not prop.range:
                continue

            # Handle Data Properties
            if isinstance(prop, DataPropertyClass):
                range_type = prop.range[0] if prop.range else str
                schema[prop.name] = self._DATATYPE_MAP.get(range_type, "str")
                continue

            # Handle Object Properties
            if isinstance(prop, ObjectPropertyClass):
                # Check for the 'acknowledgement' annotation category. This is used in the ontology
                # to mark properties that act as high-level references and should not be expanded.
                # Handle properties marked for 'acknowledgement' based on their level.
                if self.presentation_order_category_prop and "acknowledgement" in getattr(
                    prop, self.presentation_order_category_prop.name
                ):
                    if is_top_level:
                        schema[prop.name] = "str"
                    continue

                classes_to_expand = set()
                for range_expression in prop.range:
                    if isinstance(range_expression, ThingClass):
                        classes_to_expand.add(range_expression)
                    elif isinstance(range_expression, Or):  # owl:unionOf
                        for class_in_union in range_expression.Classes:
                            if isinstance(class_in_union, ThingClass):
                                classes_to_expand.add(class_in_union)
                    elif isinstance(range_expression, And):  # owl:intersectionOf
                        # This pattern is used for SKOS-based vocabularies.
                        if any(
                            c.name == "Concept"
                            for c in range_expression.Classes
                            if hasattr(c, "name")
                        ):
                            schema[prop.name] = "str"
                            continue

                if classes_to_expand and any(list(c.instances()) for c in classes_to_expand):
                    schema[prop.name] = "str"
                    continue

                unvisited_classes = {
                    c
                    for c in classes_to_expand
                    if c not in visited_classes and c.name not in ["Thing", "Concept"]
                }

                if not unvisited_classes:
                    continue

                sub_properties = set()
                for range_class in unvisited_classes:
                    sub_properties.update(self.get_all_properties_for_class(range_class))

                if sub_properties:
                    new_visited_set = visited_classes.union(unvisited_classes)
                    schema[prop.name] = self._properties_to_primitives_recursive(
                        list(sub_properties), new_visited_set, False
                    )

        return schema

    def get_all_properties_for_class(self, cls: ThingClass) -> set[PropertyClass]:
        schema = getattr(models, cls.name).model_json_schema()
        return schema

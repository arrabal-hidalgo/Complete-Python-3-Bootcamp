from collections import defaultdict
from typing import Dict, List

from owlready2 import get_ontology


class OWLParser:

    def __init__(self, uri: str, main_bussines_classes: List[str]):
        self.ontology = get_ontology(uri).load()
        # self.ontology.base_iri = f"{uri}#"
        self.main_bussines_classes = main_bussines_classes

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

    def get_classes_description(self, classes: list) -> Dict[str, str]:
        return {cl.name: cl.comment.get_lang("en").first() if cl.comment else "" for cl in classes}

    def get_classes_names(self, classes: list) -> List[str]:
        return [ontology_class.name for ontology_class in classes]

    def get_classes_from_names(self, names: List[str], classes: list) -> list:
        return [ontology_class for ontology_class in classes if ontology_class.name in names]

    def get_properties_from_classes(self, current_parents: list) -> dict:
        parents = current_parents
        restrictions: list = []
        while current_parents:
            is_a = self._extract_is_a(current_parents)
            new_parents = self.get_parents(is_a)
            new_restrictions = self._extract_restrictions(is_a)
            restrictions_parents = self.get_parents(
                [
                    restriction.value
                    for restriction in new_restrictions
                    if hasattr(restriction, "value")
                ]
            )
            restrictions = restrictions + self._extract_primitives(new_restrictions)
            current_parents = new_parents + restrictions_parents
            parents = parents + current_parents

        for parent in parents:
            restrictions = restrictions + self._extract_primitives(parent.is_a)
        restrictions = list(set(restrictions))

        return self._restrictions_to_domain_dict(restrictions)

    def _extract_is_a(self, classes: list) -> list:
        return list(set([related for ontology_class in classes for related in ontology_class.is_a]))

    def _extract_primitives(self, classes: list) -> list:
        return [
            property
            for property in classes
            if hasattr(property, "value") and property.value.__class__.__name__ != "ThingClass"
        ]

    def get_subclasses(self, classes: list) -> list:
        return [
            ontology_class
            for ontology_superclass in classes
            for ontology_class in self.ontology.get_children_of(ontology_superclass)
        ]

    def get_parents(self, is_a: list) -> list:
        return list(set([parent for parent in is_a if parent.__class__.__name__ == "ThingClass"]))

    def _extract_restrictions(self, is_a: list) -> list:
        return list(
            set(
                [
                    restriction
                    for restriction in is_a
                    if restriction.__class__.__name__ == "Restriction"
                ]
            )
        )

    def _restrictions_to_domain_dict(self, restrictions: list) -> dict:
        domain_dict: defaultdict = defaultdict(dict)
        for restriction in restrictions:
            domains = (
                restriction.property.domain.first().Classes
                if hasattr(restriction.property.domain.first(), "Classes")
                else [restriction.property.domain.first()]
            )
            for domain in domains:
                if domain is None:
                    continue
                domain_dict[domain.name][restriction.property.name] = (
                    repr(restriction.value).removeprefix("<class '").removesuffix("'>")
                )

        return domain_dict

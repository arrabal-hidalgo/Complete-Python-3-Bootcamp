from enum import Enum


class NodeType(str, Enum):
    pass


class PromptType(str, Enum):

    def __str__(self):
        return self.value

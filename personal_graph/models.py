"""
Pydantic models for pythonic API to the graph db
"""

from pydantic import BaseModel, Field
from typing import List, Union, Dict


class Node(BaseModel):
    id: Union[int, str] = Field(..., description="Unique Identifier for the node.")
    attribute: Union[str, Dict[str, str]] = Field(
        ..., description="Content or information associated with the node."
    )
    label: str = Field(..., description="Label or name associated with the node.")


class Edge(BaseModel):
    source: Union[int, str] = Field(
        ..., description="identifier of the source node from which the edge originates."
    )
    target: Union[int, str] = Field(
        ..., description="identifier of the target node to which the edge points."
    )
    label: str = Field(..., description="Label associated with the edge.")
    attribute: Union[str, Dict[str, str]] = Field(
        ..., description="This is some related attributes with the relationship."
    )


class EdgeInput(BaseModel):
    source: Node = Field(..., description="Source node from which the edge originates.")
    target: Node = Field(..., description="Target node to which the edge points.")
    label: str = Field(..., description="Label associated with the edge.")
    attribute: Union[str, Dict[str, str]] = Field(
        ..., description="Additional attributes associated with the edge."
    )


class KnowledgeGraph(BaseModel):
    nodes: List[Node] = Field(..., default_factory=list)
    edges: List[Edge] = Field(..., default_factory=list)

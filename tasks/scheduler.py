import logging
from tasks.exceptions import InvalidTaskFormat
from typing import List, Any

from networkx import Graph
from networkx.algorithms.clique import MaxWeightClique

NAME_KEY = "name"
RESOURCES_KEY = "resources"
PROFIT_KEY = "profit"


class MaxWeightTasksSelector(MaxWeightClique):  # pragma: no cover
    """
    This class is a small extension of `MaxWeightClique` from the networkx
    library, where only the following methods are overwritten:
    - __init__: only weights verification was suppressed because that didn't
        allow floats values.
    - expand: to replace the search for adjacent nodes with non-adjacent nodes.
    """

    def __init__(self, G, weight):
        self.G = G
        self.incumbent_nodes = []
        self.incumbent_weight = 0

        if weight is None:
            self.node_weights = {v: 1 for v in G.nodes()}
        else:
            for v in G.nodes():
                if weight not in G.nodes[v]:
                    errmsg = f"Node {v!r} does not have the requested weight field."
                    raise KeyError(errmsg)
            self.node_weights = {v: G.nodes[v][weight] for v in G.nodes()}

    def expand(self, C, C_weight, P):
        self.update_incumbent_if_improved(C, C_weight)
        branching_nodes = self.find_branching_nodes(P, self.incumbent_weight - C_weight)
        while branching_nodes:
            v = branching_nodes.pop()
            P.remove(v)
            new_C = C + [v]
            new_C_weight = C_weight + self.node_weights[v]
            new_P = [w for w in P if not self.G.has_edge(v, w)]
            self.expand(new_C, new_C_weight, new_P)


def are_incompatibles(t1_resources: List[Any], t2_resources: List[Any]) -> bool:
    """Decide if two tasks resources are incompatibles.

    Two tasks are incompatible if they use the same(s) resource(s).

    Examples:
        1. t1_resources = ["a", "b"], t2_resources = ["a"]
           are incompatibles because both use resource "a".
        2. t1_resources = ["b"], t2_resources = ["a"]
           are compatibles because don't share resources.

    Args:
        t1_resources, t2_resources: tasks resources to compare.

    Return:
        Boolean value that indicates if tasks resources are incompatibles.
    """
    return any(item in t2_resources for item in t1_resources) or any(
        item in t1_resources for item in t2_resources
    )


def from_tasks_to_graph(tasks: List[dict]) -> Graph:
    """Generates the graph associated to the tasks list.

    The graph nodes are each of the listed tasks, and the associated weight
    with each one is the task "profit". The graph edges are built using tasks
    "resources", where (u, v) in E if u resources is incompatibles with v
    resources.

    Example: suppose the following tasks list
        - tasks: [
            {"name": "t1", "resources": ["a", "b", "c"], "profit": 9.4},
            {"name": "t2", "resources": ["a", "d"], "profit": 1.4},
            {"name": "t3", "resources": ["b"], "profit": 3.2},
            {"name": "t4", "resources": ["c", "d"], "profit": 6.3},
        ]

    then, the associated graph is:
    G = (V, E) = ({t1, t2, t3, t4}, {(t1, t2), (t1, t3), (t1, t4), (t2, t4)})

    Args:
        tasks: list of tasks to analize.

    Return:
        The associated graph to tasks list.
    """
    graph = Graph()
    while tasks:
        t1 = tasks.pop()
        try:
            graph.add_node(t1[NAME_KEY], profit=t1[PROFIT_KEY])
        except KeyError:
            msg = (
                f"Invalid task format for task: {str(t1)}. Please, review task"
                " structure and try again."
            )
            logging.error(msg)
            raise InvalidTaskFormat(msg=msg)
        for t2 in tasks:
            if are_incompatibles(t1[RESOURCES_KEY], t2[RESOURCES_KEY]):
                graph.add_edge(t1[NAME_KEY], t2[NAME_KEY])
    return graph


def get_maximum_weighted_independient_set(graph: Graph) -> List[str]:
    """Obtains the largest nodes subset such that it maximizes the sum of
    the weights.

    Args:
        graph: graph where to search for the set.

    Returns:
        Maximum independient set.
    """
    mwts = MaxWeightTasksSelector(graph, weight=PROFIT_KEY)
    mwts.find_max_weight_clique()
    logging.info(
        "The max profit is: %d and the tasks schedule are: %s",
        mwts.incumbent_weight,
        mwts.incumbent_nodes,
    )
    return mwts.incumbent_nodes


def get_highest_profit_schedule(tasks: List[dict]) -> List[str]:  # pragma: no cover
    """Gets tasks list that generates the highest profit.

    Args:
        tasks: list of tasks to analize.

    Returns:
        List with tasks names that belong to the best schedule.
    """
    graph = from_tasks_to_graph(tasks)
    schedule = get_maximum_weighted_independient_set(graph)
    return schedule

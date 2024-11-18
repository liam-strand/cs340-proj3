from simulator.node import Node
from typing import List, Dict, Tuple, NewType
import pickle
from pprint import pformat
from collections import defaultdict


DistanceVector = NewType("DistanceVector", Dict[int, Tuple[int, List[int]]])


class Distance_Vector_Node(Node):
    def __init__(self, id):
        self.neighbor_costs: Dict[int, int] = defaultdict(lambda: float("inf"))
        self.neighbor_dvs: Dict[int, Tuple[DistanceVector, int]] = {}
        self.dv: DistanceVector = {}
        self.routes: Dict[int, int] = {}
        self.seq = 0
        super().__init__(id)

    # Return a string
    def __str__(self):
        return f""" NODE {self.id}:
        dv = {pformat(self.dv)}
        routes = {pformat(self.routes)}
        neighbors = {pformat(self.neighbors)}
        neighbor_costs = {pformat(self.neighbor_costs)}
        neighbor_dvs = {pformat(self.neighbor_dvs)}
        """

    def link_has_been_updated(self, neighbor, latency):
        # latency = -1 if delete a link
        if latency == -1:
            self.neighbors.remove(neighbor)
            self.neighbor_costs.pop(neighbor)
            self.neighbor_dvs.pop(neighbor)
        else:
            if neighbor not in self.neighbor_costs:
                self.neighbors.append(neighbor)
                self.neighbor_dvs[neighbor] = ({}, -1)

            self.neighbor_costs[neighbor] = latency
        self.logging.debug(f"change in link {self.id} => {neighbor} = {latency}")

        self.recalculate_dv()

    def process_incoming_routing_message(self, m):
        sender, vector, seq = pickle.loads(m)

        if sender in self.neighbor_dvs:
            _, old_seq = self.neighbor_dvs[sender]
            if old_seq > seq:
                return

        self.logging.debug(f"NOW = {self.get_time()}")
        self.logging.debug(f"new DV from {sender} @ {seq}: {vector}")
        self.neighbor_dvs[sender] = (vector, seq)

        self.recalculate_dv()

    def recalculate_dv(self):
        changed = False
        all_nodes = set()

        for v, (n_dv, _) in self.neighbor_dvs.items():
            all_nodes.add(v)
            all_nodes = all_nodes.union(set(n_dv.keys()))

        if self.id in all_nodes:
            all_nodes.remove(self.id)

        for y in sorted(all_nodes):
            options = []

            if y in self.neighbors:
                options.append((self.neighbor_costs[y], y))

            for v in self.neighbors:
                neighbor_dv, _ = self.neighbor_dvs[v]
                if y in neighbor_dv:
                    dv_cost, dv_path = neighbor_dv[y]
                    if self.id not in dv_path:
                        op_cost = self.neighbor_costs[v] + dv_cost
                        options.append((op_cost, v))

            self.logging.debug(f"options for {y} = {options}")
            if options == []:
                if y in self.dv:
                    if not changed:
                        changed = True
                    self.dv.pop(y)
                    self.routes.pop(y)

            else:
                best_cost, best_next = min(options)
                if best_next == y:
                    if not changed and (
                        y not in self.dv or self.dv[y] != (best_cost, [y])
                    ):
                        changed = True
                    self.dv[y] = (best_cost, [y])
                    self.routes[y] = y
                else:
                    neighbor_path = self.neighbor_dvs[best_next][0][y][1]
                    best_route = neighbor_path + [best_next]
                    if not changed and (
                        y not in self.dv or self.dv[y] != (best_cost, best_route)
                    ):
                        changed = True
                    self.dv[y] = (best_cost, best_route)
                    self.routes[y] = best_next

        if changed:
            self.seq += 1
            self.send_to_neighbors(pickle.dumps((self.id, self.dv, self.seq)))

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination):
        if destination not in self.routes:
            return -1

        return self.routes[destination]


def dvtostr(dv: DistanceVector) -> str:
    res = "\n"
    for k in sorted(dv):
        cost, path = dv[k]
        res += f"{k:3} @ {cost:3} : {path}\n"
    return res

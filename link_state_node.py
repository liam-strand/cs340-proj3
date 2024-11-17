from simulator.node import Node
from typing import Dict, Tuple, DefaultDict
from collections import defaultdict
import pickle
import itertools
from heapq import heappush, heappop, heapify
import pprint


class Link_State_Node(Node):
    def __init__(self, id: int):
        self.links: DefaultDict[int, Dict[int, Tuple[int, int]]] = defaultdict(dict)
        super().__init__(id)

    # Return a string
    def __str__(self) -> str:
        return f"{self.id}:\n{pprint.pformat(self.links)}"

    # Fill in this function
    def link_has_been_updated(self, neighbor: int, latency: int) -> None:
        if latency == -1:
            old_latency, old_seq = self.links[self.id].pop(neighbor)
            self.links[neighbor].pop(self.id)
            self.neighbors.remove(neighbor)
            seq = old_seq + 1
        else:
            if neighbor not in self.neighbors:
                seq = 0
                self.neighbors.append(neighbor)
                for src in self.links:
                    for dest, (old_latency, old_seq) in self.links[src].items():
                        self.logging.debug(
                            f"telling {neighbor} about {src} => {dest} = {old_latency}"
                        )
                        self.send_to_neighbor(
                            neighbor,
                            pickle.dumps((self.id, src, dest, old_latency, old_seq)),
                        )
            else:
                old_latency, old_seq = self.links[self.id][neighbor]
                seq = old_seq + 1

            self.logging.debug(f"{self.id} => {neighbor} = {latency}")
            self.links[self.id][neighbor] = (latency, seq)
            self.links[neighbor][self.id] = (latency, seq)

        for neigh in filter(lambda n: n != neighbor, self.neighbors):
            self.send_to_neighbor(
                neigh, pickle.dumps((self.id, self.id, neighbor, latency, seq))
            )

    # Fill in this function
    def process_incoming_routing_message(self, m: str) -> None:
        sender, src, dest, latency, seq = pickle.loads(m)

        if dest in self.links[src]:
            old_latency, old_seq = self.links[src][dest]
            if old_seq > seq:
                message = (self.id, src, dest, old_latency, old_seq)
                self.send_to_neighbor(sender, pickle.dumps(message))
                return
            if old_seq == seq:
                return

        self.links[src][dest] = (latency, seq)
        self.links[dest][src] = (latency, seq)

        for neighbor in filter(lambda n: n != sender, self.neighbors):
            self.send_to_neighbor(
                neighbor, pickle.dumps((self.id, src, dest, latency, seq))
            )

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination: int) -> int:
        preds = self.dijkstra()

        self.logging.debug(pprint.pformat(preds))

        if destination not in preds:
            self.logging.info(f"{destination} is not reachable from {self.id}")
            return -1

        path = [destination]

        while path[-1] != self.id:
            path.append(preds[path[-1]])
        self.logging.info(f"{self.id} to {destination} is {path}")
        return path[-2]

    def dijkstra(self) -> Dict[int, int]:

        self.logging.debug(pprint.pformat(self.links))

        working_graph = {k: DKNode(float("inf"), None) for k in self.links.keys()}

        working_graph[self.id].d = 0

        seen = set()
        queue = PQueue()

        for k, v in working_graph.items():
            queue.push(k, v.d)

        self.logging.debug(queue)
        while not queue.is_empty():
            w, u = queue.pop()
            self.logging.debug(f"got {w} {u}")
            self.logging.debug(queue)
            seen.add(u)
            for neighbor in self.links[u].keys():
                latency, _ = self.links[u][neighbor]
                new_w = w + latency
                self.logging.debug(f"{w} {latency} {new_w} {working_graph[neighbor].d}")

                if working_graph[neighbor].d > new_w:
                    working_graph[neighbor].pi = u
                    working_graph[neighbor].d = new_w
                    queue.push(neighbor, new_w)

        return {k: v.pi for k, v in working_graph.items()}


class PQueue:
    def __init__(self):
        self.pq = []
        self.mapping = {}
        self.counter = itertools.count()

    def __str__(self):
        return str(self.pq)

    def push(self, item, priority):
        if item in self.mapping:
            self.remove(item)
        count = next(self.counter)
        entry = [priority, count, item]
        self.mapping[item] = entry
        heappush(self.pq, entry)

    def remove(self, item):
        entry = self.mapping.pop(item)
        self.pq.remove(entry)
        heapify(self.pq)

    def pop(self):
        while self.pq:
            priority, count, item = heappop(self.pq)
            if item is not None:
                self.mapping.pop(item)
                return priority, item
        return None

    def is_empty(self) -> bool:
        return len(self.pq) == 0


class DKNode:
    def __init__(self, d, pi):
        self.d = d
        self.pi = pi

    def __repr__(self):
        return f"(d={self.d}, pi={self.pi})"

from simulator.node import Node
from typing import Dict, Tuple, DefaultDict, Set
from collections import defaultdict
import pickle
import itertools
from heapq import heappush, heappop, heapify
from pprint import pformat


class Link_State_Node(Node):
    def __init__(self, id: int):
        self.links: DefaultDict[int, Dict[int, Tuple[int, int]]] = defaultdict(dict)
        self.removed: Dict[Tuple[int, int], int] = {}
        self.routes: Dict[int, int] = {}
        self.stale = True
        super().__init__(id)

    # Return a string
    def __str__(self) -> str:
        return f"STATE: \n{pformat(self.links)}\nROUTES: \n{pformat(self.routes)}"

    # Fill in this function
    def link_has_been_updated(self, neighbor: int, latency: int) -> None:
        self.stale = True
        if latency == -1:
            old_latency, old_seq = self.links[self.id].pop(neighbor)
            self.links[neighbor].pop(self.id)
            self.neighbors.remove(neighbor)
            self.logging.debug(f"{self.id} =/ {neighbor}")
            self.removed[(self.id, neighbor)] = self.get_time()
            self.removed[(neighbor, self.id)] = self.get_time()
        else:
            if neighbor not in self.neighbors:
                self.neighbors.append(neighbor)
                for src in self.links:
                    for dest, (old_latency, old_seq) in self.links[src].items():
                        self.logging.debug(
                            f"telling {neighbor} about {src} => {dest} = {old_latency}"
                        )
                        self.send_to_neighbor(
                            neighbor,
                            pickle.dumps(
                                (self.id, src, dest, old_latency, old_seq)),
                        )
            else:
                old_latency, old_seq = self.links[self.id][neighbor]

            self.logging.debug(f"{self.id} => {neighbor} = {latency}")
            self.links[self.id][neighbor] = (latency, self.get_time())
            self.links[neighbor][self.id] = (latency, self.get_time())

            if (self.id, neighbor) in self.removed:
                self.removed.pop((self.id, neighbor))
                self.removed.pop((neighbor, self.id))

        for neigh in filter(lambda n: n != neighbor, self.neighbors):
            self.send_to_neighbor(
                neigh, pickle.dumps((self.id, self.id, neighbor, latency, self.get_time()))
            )

    # Fill in this function
    def process_incoming_routing_message(self, m: str) -> None:
        self.stale = True
        sender, src, dest, latency, seq = pickle.loads(m)
        self.logging.debug(f"got message {(sender, src, dest, latency, seq)}")

        if latency == -1 and dest not in self.links[src]:
            return

        if dest in self.links[src]:
            old_latency, old_seq = self.links[src][dest]
            if old_seq > seq:
                message = (self.id, src, dest, old_latency, old_seq)
                self.send_to_neighbor(sender, pickle.dumps(message))
                return
            if old_seq == seq:
                return
            if latency == -1:
                self.logging.debug(f"popping {src} => {dest}")
                self.links[src].pop(dest)
                self.links[dest].pop(src)
                self.removed[(src, dest)] = seq
                self.removed[(dest, src)] = seq

        if latency != -1:
            if (src, dest) not in self.removed or self.removed[(src, dest)] < seq:
                self.logging.debug(f"adding {src} => {dest}")
                self.links[src][dest] = (latency, seq)
                self.links[dest][src] = (latency, seq)

                if (src, dest) in self.removed:
                    self.removed.pop((src, dest))
                    self.removed.pop((dest, src))
            elif self.removed[(src, dest)] > seq:
                return

        for neighbor in filter(lambda n: n != sender, self.neighbors):
            self.send_to_neighbor(
                neighbor, pickle.dumps((self.id, src, dest, latency, seq))
            )

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination: int) -> int:
        if self.stale:
            self.logging.debug("Rebuilding routes")
            working_graph = defaultdict(set)
            self.routes = {}
            self.logging.debug("starting dijkstra")
            preds = self.dijkstra()
            self.logging.debug("building working_graph")
            for node, pred in preds.items():
                working_graph[pred].add(node)
            self.logging.debug(f"WG = {pformat(working_graph)}")
            for next in working_graph[self.id]:
                children = self.get_all_children(working_graph, next)
                self.logging.debug(f"{next} can reach {children}")
                self.routes[next] = next
                for child in children:
                    self.routes[child] = next
            self.stale = False

        if destination not in self.routes:
            self.logging.debug(
                f"{destination} is not reachable from {self.id}")
            return -1

        return self.routes[destination]

    def dijkstra(self) -> Dict[int, int]:
        working_graph = {k: DKNode(float("inf"), None)
                         for k in self.links.keys()}

        self.logging.debug(f"D links = {pformat(self.links)}")

        working_graph[self.id].d = 0

        seen = set()
        queue = PQueue()

        for k, v in working_graph.items():
            queue.push(k, v.d)

        self.logging.debug(pformat(queue))
        count = 0
        
        while not queue.is_empty():
            count += 1
            w, u = queue.pop()
            seen.add(u)
            self.logging.debug(f"inspecting {u}")
            self.logging.debug(f"queue = {queue}")
            self.logging.debug(f"seen  = {seen}")
            for neighbor in filter(lambda n: n not in seen, self.links[u].keys()):
                latency, _ = self.links[u][neighbor]
                new_w = w + latency

                if working_graph[neighbor].d > new_w:
                    working_graph[neighbor].pi = u
                    working_graph[neighbor].d = new_w
                    queue.push(neighbor, new_w)

            if count > 1000:
                exit(1)

        return {k: v.pi for k, v in working_graph.items()}

    def get_all_children(self, graph: Dict[int, Set[int]], root: int) -> Set[int]:
        seen = set(graph[root])
        for child in graph[root]:
            subchildren = self.get_all_children(graph, child)
            for found in subchildren:
                seen.add(found)
        return seen


class PQueue:
    def __init__(self):
        self.pq = []
        self.mapping = {}
        self.counter = itertools.count()

    def __repr__(self):
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

from file_parser import get_file_path, Parser, ParseError, ZoneType
from utils import AdjacencyList
from collections import defaultdict
import sys
import heapq


class Drone:
    def __init__(self, drone_id, position):
        self.id = drone_id
        self.position = position
        self.path = []
        self.arrived = False


class Dijkstra:
    def __init__(self, graph, zones):
        self.graph = graph
        self.zones = zones
        self.hub_cache = {}
        self.link_cache = {}

    def _reconstruct_path(self, prev, turns, start, end, transit):
        path = []
        node = end

        if prev[node] is None and node != start:
            return []

        while node is not None:
            path.append((node, turns[node], "zone"))

            if prev[node] is not None:
                destination_zone = self.zones[node]
                if destination_zone.zone_type == ZoneType.RESTRICTED:
                    connection_name = f"{prev[node]}-{node}"
                    transit_turn = turns[node] - 1
                    path.append((connection_name, transit_turn, "transit"))

            node = prev[node]

        path.reverse()
        return path

    def find_path(self, drone, start, end, current_turn):
        heap = []
        dist = {zone: float('inf') for zone in self.graph._data}
        dist[start] = 0
        visited = set()
        prev = {zone: None for zone in self.graph._data}
        turns = {zone: 0 for zone in self.graph._data}
        turns[start] = current_turn
        heapq.heappush(heap, (0, current_turn, start))
        transit = {}
        while (heap):
            cost, turn, node = heapq.heappop(heap)
            if (node, turn) in visited:
                continue
            visited.add((node, turn))
            if node == end:
                break
            neighbors = self.graph.get_neighbors(node)
            for entry in neighbors:
                neighbor = entry.neighbor
                if neighbor.zone_type == ZoneType.BLOCKED:
                    continue
                arrival_turn = turn + entry.cost

                key = (neighbor.name, arrival_turn)
                key_link = (
                    min(node, neighbor.name),
                    max(node, neighbor.name), turn)
                reserved = self.hub_cache.get(key, 0)
                reserved_link = self.link_cache.get(key_link, 0)
                if reserved_link >= entry.connection.max_link_capacity:
                    continue
                if reserved >= neighbor.max_drones:
                    continue
                new_cost = cost + entry.cost
                if new_cost < dist[neighbor.name]:
                    dist[neighbor.name] = new_cost
                    prev[neighbor.name] = node
                    turns[neighbor.name] = arrival_turn

                    heapq.heappush(
                        heap,
                        (new_cost, arrival_turn, neighbor.name)
                    )
                if neighbor.zone_type == ZoneType.RESTRICTED:
                    transit[neighbor.name] = arrival_turn + 1
            wait_turn = turn + 1
            wait_key = (node, wait_turn)

            current_zone = self.zones[node]
            reserved = self.hub_cache.get(wait_key, 0)
            if reserved < current_zone.max_drones:
                heapq.heappush(heap, (cost + 1, wait_turn, node))
        path = self._reconstruct_path(prev, turns, start, end, transit)
        for zone, turn, state in path:
            if state == "zone":
                key = (zone, turn)
                self.hub_cache[key] = self.hub_cache.get(key, 0) + 1
        for i in range(len(path) - 1):
            zone_a, turn_a, _ = path[i]
            zone_b, turn_b, _ = path[i + 1]

            key = (
                min(zone_a, zone_b),
                max(zone_a, zone_b),
                turn_a
            )
            self.link_cache[key] = self.link_cache.get(key, 0) + 1
        return path


class Simulation:
    def __init__(self, graph, drones, dijkstra):
        self.graph = graph
        self.drones = drones
        self.dijkstra = dijkstra
        self.max_turn = 0

    def run(self):
        movements = defaultdict(list)
        for d in self.drones:
            path = self.dijkstra.find_path(
                d, d.position, self.graph.end.name, 0)
            d.path = path
        for d in self.drones:
            last_turn = d.path[-1][1]
            if last_turn > self.max_turn:
                self.max_turn = last_turn
        for drone in self.drones:
            for (zone, turn, state) in drone.path:
                if turn == 0 or zone == "start":
                    continue
                movements[turn].append((drone.id, zone))
        for turn in sorted(movements.keys()):
            line = ""
            for drone_id, zone in movements[turn]:
                line += f"{drone_id}-{zone} "
            print(line.strip())


if __name__ == "__main__":
    path = get_file_path()
    try:
        parsed_data = Parser(path).parse()
    except (ParseError, FileNotFoundError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    # print(f"nb_drones : {parsed_data.nb_drones}")
    list_drones = []
    for i in range(1, parsed_data.nb_drones + 1):
        D = Drone(f"D{i}", parsed_data.start.name)
        list_drones.append(D)

    adj = AdjacencyList()

    for zone in parsed_data.zones.values():
        adj.add_zone(zone)

    for connection in parsed_data.connections:
        zone_a = parsed_data.zones[connection.zone1]
        zone_b = parsed_data.zones[connection.zone2]
        adj.add_connection(zone_a, zone_b, connection)
    dijkstra = Dijkstra(adj, parsed_data.zones)
    for d in list_drones:
        path = dijkstra.find_path(d, d.position, parsed_data.end.name, 0)
        d.path = path

    for d in list_drones:
        print(f"{d.path}\n")
    simulation = Simulation(parsed_data, list_drones, dijkstra)
    simulation.run()

import sys
from file_parser import Parser, get_file_path, ParseError, ZoneType


class AdjacencyEntry:
    """One neighbor entry in the adjacency list."""

    def __init__(self, neighbor_zone, cost, connection):
        self.neighbor = neighbor_zone
        self.cost = cost
        self.connection = connection


class AdjacencyList:
    """Represents the graph as a dictionary of neighbor lists."""

    def __init__(self):
        self._data = {}
        self.zones = []

    def add_zone(self, zone):
        """Register a zone using its name as key."""
        if zone.name not in self._data:
            self._data[zone.name] = []
            self.zones.append(zone)

    def add_connection(self, zone_a, zone_b, connection):
        """Add a bidirectional connection between two Zone objects."""
        cost_a_to_b = self._get_cost(zone_b)
        cost_b_to_a = self._get_cost(zone_a)

        self._data[zone_a.name].append(
            AdjacencyEntry(zone_b, cost_a_to_b, connection)
        )
        self._data[zone_b.name].append(
            AdjacencyEntry(zone_a, cost_b_to_a, connection)
        )

    def get_neighbors(self, zone_name):
        """Return all neighbors of a zone by name."""
        return self._data.get(zone_name, [])
        
    def get_neighbor_entries(self, zone):
        """Return raw AdjacencyEntry objects (for algorithms that need cost/connection)."""
        name = zone.name if hasattr(zone, 'name') else zone
        return self._data.get(name, [])

    def _get_cost(self, zone):
        """Calculate movement cost based on destination zone type."""
        if zone.zone_type == ZoneType.RESTRICTED:
            return 2
        elif zone.zone_type == ZoneType.BLOCKED:
            return float('inf')
        else:
            return 1


def test_adjacency(adj_list, all_zones):
    for zone in all_zones:
        neighbors = adj_list.get_neighbors(zone.name)
        print(f"\nZone: {zone.name}")
        for entry in neighbors:
            print(f"  → {entry.neighbor.name}"
                  f"  cost={entry.cost}"
                  f"  link_capacity={entry.connection.max_link_capacity}")


if __name__ == "__main__":
    path = get_file_path()
    try:
        parsed_data = Parser(path).parse()
    except (ParseError, FileNotFoundError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    adj = AdjacencyList()

    for zone in parsed_data.zones.values():      # ← .values() not .keys()
        adj.add_zone(zone)

    for connection in parsed_data.connections:
        zone_a = parsed_data.zones[connection.zone1]  # ← string → Zone object
        zone_b = parsed_data.zones[connection.zone2]  # ← string → Zone object
        adj.add_connection(zone_a, zone_b, connection)

    test_adjacency(adj, parsed_data.zones.values())

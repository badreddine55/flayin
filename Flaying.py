
import sys
from file_parser import get_file_path, Parser, ParseError
from utils import AdjacencyList
from algorithm import Drone, Dijkstra, Simulation
from py_graphic import Game

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
    print(f"Drone {d.id} path:")
    for zone, turn, state in d.path:
        print(f"  turn {turn} → {zone} -> {state}")
    print("------")
simulation = Simulation(parsed_data, list_drones, dijkstra)
simulation.run()


game = Game()
game.set_data(adj)
game.set_drones(list_drones)
game.run()

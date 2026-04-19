"""
Fly-in drone routing system — map file parser.

Parses a .map file into a structured Graph object containing zones,
connections, and drone count metadata.
"""

import sys
from enum import Enum
from typing import Generator, Optional


class ParseError(Exception):
    """Raised when the map file contains a syntax or semantic error.

    Attributes:
        line_number: The 1-based line number where the error was detected.
        cause: A human-readable description of the problem.
    """

    def __init__(self, line_number: int, cause: str) -> None:
        """Initialize ParseError with location and cause.

        Args:
            line_number: 1-based line number in the source file.
            cause: Description of the parsing problem.
        """
        super().__init__(f"Line {line_number}: {cause}")
        self.line_number: int = line_number
        self.cause: str = cause


class ZoneType(Enum):
    """Possible zone types that affect movement cost and accessibility.

    Values:
        NORMAL:     Standard zone, costs 1 turn to enter (default).
        BLOCKED:    Inaccessible — no drone may enter or pass through.
        RESTRICTED: Sensitive zone, costs 2 turns to enter.
        PRIORITY:   Preferred zone, costs 1 turn but favoured by pathfinding.
    """

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Zone:
    """Represents a single node (hub) in the drone network graph.

    Attributes:
        name:       Unique identifier. No dashes or spaces allowed.
        coordinates: (x, y) integer position on the map.
        zone_type:  Movement cost / accessibility type.
        color:      Optional display colour for visual output.
        max_drones: Maximum drones that may occupy this zone simultaneously.
        role:       One of ``"hub"``, ``"start"``, or ``"end"``.
    """

    def __init__(
        self,
        name: str,
        coordinates: tuple[int, int],
        zone_type: ZoneType = ZoneType.NORMAL,
        color: Optional[str] = None,
        max_drones: int = 1,
        role: str = "hub",
    ) -> None:
        """Create a Zone.

        Args:
            name:        Unique zone identifier (no dashes, no spaces).
            coordinates: Integer (x, y) position.
            zone_type:   Movement cost type (default: NORMAL).
            color:       Optional single-word colour string (default: None).
            max_drones:  Maximum simultaneous occupants (default: 1).
            role:        ``"hub"``, ``"start"``,
            or ``"end"`` (default: ``"hub"``).
        """
        self.name: str = name
        self.coordinates: tuple[int, int] = coordinates
        self.zone_type: ZoneType = zone_type
        self.color: Optional[str] = color
        self.max_drones: int = max_drones
        self.role: str = role

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"Zone(name={self.name!r}, type={self.zone_type.value}, "
            f"coords={self.coordinates}, max={self.max_drones},"
            f" role={self.role})"
        )


class Connection:
    """Represents a bidirectional edge between two zones in the graph.

    Attributes:
        zone1:            Name of the first zone.
        zone2:            Name of the second zone.
        max_link_capacity: Maximum drones that may traverse this edge
                           simultaneously (default: 1).
    """

    def __init__(
        self,
        zone1: str,
        zone2: str,
        max_link_capacity: int = 1,
    ) -> None:
        """Create a Connection between two zones.

        Args:
            zone1:             Name of the first endpoint zone.
            zone2:             Name of the second endpoint zone.
            max_link_capacity: Simultaneous drone traversal limit (default: 1).
        """
        self.zone1: str = zone1
        self.zone2: str = zone2
        self.max_link_capacity: int = max_link_capacity

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"Connection({self.zone1!r} <-> {self.zone2!r}, "
            f"capacity={self.max_link_capacity})"
        )


class Graph:
    """The complete in-memory representation of a parsed drone network.

    Attributes:
        nb_drones:   Total number of drones that must travel start → end.
        zones:       Mapping of zone name to Zone object.
        connections: All connections in the network.
        start:       The unique departure zone.
        end:         The unique destination zone.
    """

    def __init__(
        self,
        nb_drones: int,
        zones: dict[str, Zone],
        connections: list[Connection],
        start: Zone,
        end: Zone,
    ) -> None:
        """Create a Graph.

        Args:
            nb_drones:   Number of drones.
            zones:       Dict mapping zone name → Zone.
            connections: List of all Connection objects.
            start:       Starting zone (role == ``"start"``).
            end:         Ending zone (role == ``"end"``).
        """
        self.nb_drones: int = nb_drones
        self.zones: dict[str, Zone] = zones
        self.connections: list[Connection] = connections
        self.start: Zone = start
        self.end: Zone = end

    def get_neighbors(self, zone_name: str) -> list[Zone]:
        """Return all zones directly reachable from *zone_name*.

        Args:
            zone_name: The name of the source zone.

        Returns:
            List of Zone objects connected to the given zone.
        """
        neighbors: list[Zone] = []
        for conn in self.connections:
            if conn.zone1 == zone_name and conn.zone2 in self.zones:
                neighbors.append(self.zones[conn.zone2])
            elif conn.zone2 == zone_name and conn.zone1 in self.zones:
                neighbors.append(self.zones[conn.zone1])
        return neighbors

    def get_connection(self, zone_a: str, zone_b: str) -> Optional[Connection]:
        """Return the Connection between *zone_a* and *zone_b*, or None.

        The lookup is order-independent (bidirectional).

        Args:
            zone_a: Name of the first zone.
            zone_b: Name of the second zone.

        Returns:
            The matching Connection, or None if no direct edge exists.
        """
        for conn in self.connections:
            if (conn.zone1 == zone_a and conn.zone2 == zone_b) or \
               (conn.zone1 == zone_b and conn.zone2 == zone_a):
                return conn
        return None

    def is_blocked(self, zone_name: str) -> bool:
        """Return True if the named zone has type BLOCKED.

        Args:
            zone_name: Name of the zone to check.

        Returns:
            True when the zone is BLOCKED, False otherwise (or if not found).
        """
        zone = self.zones.get(zone_name)
        if zone is None:
            return False
        return zone.zone_type == ZoneType.BLOCKED

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"Graph(drones={self.nb_drones}, zones={len(self.zones)}, "
            f"connections={len(self.connections)}, "
            f"start={self.start.name!r}, end={self.end.name!r})"
        )


class Parser:
    """Reads and validates a .map file, producing a Graph object.

    Usage::

        parser = Parser("maps/example.map")
        graph  = parser.parse()

    Attributes:
        file_path: Path to the .map file supplied at construction time.
    """

    def __init__(self, file_path: str) -> None:
        """Initialise the parser with a file path.

        Args:
            file_path: Absolute or relative path to the .map file.
        """
        self.file_path: str = file_path

    def parse(self) -> Graph:
        """Parse the map file and return a validated Graph.

        Returns:
            A fully constructed Graph object.

        Raises:
            ParseError:      On any syntax or semantic error in the file.
            FileNotFoundError: If the file does not exist.
        """
        zones: dict[str, Zone] = {}
        connections: list[Connection] = []
        seen_connections: set[frozenset[str]] = set()
        start_zone: Optional[Zone] = None
        end_zone: Optional[Zone] = None
        nb_drones: int = 0
        nb_drones_parsed: bool = False

        for line_number, raw_line in self._read_lines():
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if not nb_drones_parsed:
                nb_drones = self._parse_nb_drones(line, line_number)
                nb_drones_parsed = True
                continue

            if line.startswith("start_hub:"):
                if start_zone is not None:
                    raise ParseError(
                        line_number, "only one start_hub is allowed")
                zone = self._parse_zone_line(
                    line, "start_hub:", "start", line_number)
                start_zone = zone

            elif line.startswith("end_hub:"):
                if end_zone is not None:
                    raise ParseError(
                        line_number, "only one end_hub is allowed")
                zone = self._parse_zone_line(
                    line, "end_hub:", "end", line_number)
                end_zone = zone

            elif line.startswith("hub:"):
                zone = self._parse_zone_line(line, "hub:", "hub", line_number)

            elif line.startswith("connection:"):
                conn = self._parse_connection_line(
                    line, zones, seen_connections, line_number
                )
                connections.append(conn)
                continue

            else:
                raise ParseError(
                    line_number, f"unrecognised line prefix: {line!r}")

            if zone.name in zones:
                raise ParseError(
                    line_number, f"duplicate zone name {zone.name!r}")
            zones[zone.name] = zone

        if not nb_drones_parsed:
            raise ParseError(
                1, "file is empty or missing 'nb_drones:' declaration")
        if start_zone is None:
            raise ParseError(0, "missing start_hub declaration")
        if end_zone is None:
            raise ParseError(0, "missing end_hub declaration")

        return Graph(
            nb_drones=nb_drones,
            zones=zones,
            connections=connections,
            start=start_zone,
            end=end_zone,
        )

    def _read_lines(self) -> Generator[tuple[int, str], None, None]:
        """Yield (1-based line number, raw line) for every line in the file.

        Yields:
            Tuples of (line_number, raw_line_text).

        Raises:
            FileNotFoundError: If self.file_path does not exist.
        """
        with open(self.file_path, "r") as fh:
            for line_number, line in enumerate(fh, start=1):
                yield line_number, line

    def _parse_nb_drones(self, line: str, line_number: int) -> int:
        """Parse and validate the ``nb_drones:`` declaration.

        Args:
            line:        The stripped source line.
            line_number: Current line number for error reporting.

        Returns:
            The validated positive integer drone count.

        Raises:
            ParseError: If the format is wrong
            or the value is not a positive integer.
        """
        if not line.startswith("nb_drones:"):
            raise ParseError(
                line_number,
                f"expected 'nb_drones: <number>' as the first declaration, "
                f"got: {line!r}",
            )
        parts = line.split(":", 1)
        raw_value = parts[1].strip()
        if not raw_value.isdigit():
            raise ParseError(
                line_number,
                f"'nb_drones' value must be a "
                f"positive integer, got {raw_value!r}",
            )
        value = int(raw_value)
        if value <= 0:
            raise ParseError(line_number, "'nb_drones' must be greater than 0")
        return value

    def _parse_zone_line(
        self,
        line: str,
        prefix: str,
        role: str,
        line_number: int,
    ) -> Zone:
        """Parse a hub / start_hub / end_hub line into a Zone object.

        Expected format (metadata optional)::

            <prefix> <name> <x> <y> [zone=<type> color=<value> max_drones=<n>]

        Args:
            line:        The full stripped source line.
            prefix:      The leading token including colon (e.g. ``"hub:"``).
            role:        Zone role string — ``"hub"``,
            ``"start"``, or ``"end"``.
            line_number: Current line number for error reporting.

        Returns:
            A fully constructed Zone object.

        Raises:
            ParseError: On any syntax or value error in the zone declaration.
        """
        value = line[len(prefix):].strip()
        parts = value.split(maxsplit=3)

        if len(parts) < 3:
            raise ParseError(
                line_number,
                f"zone line requires at least name, x, y — got: {value!r}",
            )

        name: str = parts[0]
        if "-" in name:
            raise ParseError(
                line_number,
                f"zone name {name!r} contains a dash, which is forbidden "
                "(dashes are used as connection separators)",
            )
        if " " in name:
            raise ParseError(
                line_number, f"zone name {name!r} must not contain spaces")

        try:
            x = int(parts[1])
            y = int(parts[2])
        except ValueError:
            raise ParseError(
                line_number,
                f"zone coordinates must be integers, "
                f"got x={parts[1]!r} y={parts[2]!r}",
            )

        raw_metadata = parts[3] if len(parts) > 3 else None
        meta = self._parse_metadata(raw_metadata, line_number)

        return Zone(
            name=name,
            coordinates=(x, y),
            zone_type=meta["zone_type"],
            color=meta["color"],
            max_drones=meta["max_drones"],
            role=role,
        )

    def _parse_metadata(
        self,
        raw: Optional[str],
        line_number: int,
    ) -> dict[str, object]:
        """Parse and validate the optional ``[key=value ...]`` metadata block.

        Args:
            raw:         The raw metadata string including brackets, or None.
            line_number: Current line number for error reporting.

        Returns:
            Dict with keys ``"zone_type"``
            (ZoneType), ``"color"`` (str | None),
            and ``"max_drones"`` (int).

        Raises:
            ParseError: On malformed brackets, unknown keys, or invalid values.
        """
        result: dict[str, object] = {
            "zone_type": ZoneType.NORMAL,
            "color": None,
            "max_drones": 1,
        }

        if raw is None:
            return result

        if not (raw.startswith("[") and raw.endswith("]")):
            raise ParseError(
                line_number,
                f"metadata block must be wrapped in [ ], got: {raw!r}",
            )

        content = raw[1:-1].strip()
        if not content:
            return result

        valid_keys = {"zone", "color", "max_drones"}

        for token in content.split():
            if "=" not in token:
                raise ParseError(
                    line_number,
                    f"metadata token {token!r} is not in key=value format",
                )
            key, value = token.split("=", 1)

            if key not in valid_keys:
                raise ParseError(
                    line_number,
                    f"unknown metadata key {key!r}; "
                    f"allowed keys are: {', '.join(sorted(valid_keys))}",
                )

            if key == "zone":
                try:
                    result["zone_type"] = ZoneType(value)
                except ValueError:
                    allowed = ", ".join(t.value for t in ZoneType)
                    raise ParseError(
                        line_number,
                        f"invalid zone type {value!r}; "
                        f"allowed values: {allowed}",
                    )

            elif key == "color":
                if not value or " " in value:
                    raise ParseError(
                        line_number,
                        f"color must be a single "
                        f"non-empty word, got {value!r}",
                    )
                result["color"] = value

            elif key == "max_drones":
                if not value.isdigit() or int(value) <= 0:
                    raise ParseError(
                        line_number,
                        f"max_drones must be a "
                        f"positive integer, got {value!r}",
                    )
                result["max_drones"] = int(value)

        return result

    def _parse_connection_line(
        self,
        line: str,
        zones: dict[str, Zone],
        seen: set[frozenset[str]],
        line_number: int,
    ) -> Connection:
        """Parse a ``connection:`` line into a Connection object.

        Expected format::

            connection: <zone1>-<zone2> [max_link_capacity=<n>]

        Args:
            line:        The full stripped source line.
            zones:       Already-parsed zones (for existence validation).
            seen:        Set of already-parsed connection pairs (dedup guard).
            line_number: Current line number for error reporting.

        Returns:
            A fully constructed Connection object.

        Raises:
            ParseError: If zones are undefined, the connection is a duplicate,
                        or the capacity value is invalid.
        """
        value = line.split(":", 1)[1].strip()
        parts = value.split(maxsplit=1)

        if not parts:
            raise ParseError(
                line_number, "connection line is empty after 'connection:'")

        zone_pair = parts[0].split("-")
        if len(zone_pair) != 2 or not zone_pair[0] or not zone_pair[1]:
            raise ParseError(
                line_number,
                f"connection must follow the format "
                f"zone1-zone2, got {parts[0]!r}",
            )

        zone1_name, zone2_name = zone_pair[0], zone_pair[1]

        for name in (zone1_name, zone2_name):
            if name not in zones:
                raise ParseError(
                    line_number,
                    f"connection references undefined zone {name!r} "
                    "(zones must be declared before their connections)",
                )

        key: frozenset[str] = frozenset({zone1_name, zone2_name})
        if key in seen:
            raise ParseError(
                line_number,
                f"duplicate connection between "
                f"{zone1_name!r} and {zone2_name!r}",
            )
        seen.add(key)

        max_link_capacity = 1
        if len(parts) > 1:
            raw_meta = parts[1].strip()
            if not (raw_meta.startswith("[") and raw_meta.endswith("]")):
                raise ParseError(
                    line_number,
                    f"connection metadata must be in [ ], got {raw_meta!r}",
                )
            content = raw_meta[1:-1].strip()
            if not content.startswith("max_link_capacity="):
                raise ParseError(
                    line_number,
                    f"only 'max_link_capacity' is valid in "
                    f"connection metadata, got {content!r}",
                )
            cap_str = content.split("=", 1)[1]
            if not cap_str.isdigit() or int(cap_str) <= 0:
                raise ParseError(
                    line_number,
                    f"max_link_capacity must be a "
                    f"positive integer, got {cap_str!r}",
                )
            max_link_capacity = int(cap_str)

        return Connection(zone1_name, zone2_name, max_link_capacity)


def get_file_path() -> str:
    """Read the map file path from command-line arguments.

    Returns:
        The file path string provided as the first CLI argument.

    Raises:
        SystemExit: If the wrong number of arguments is supplied.
    """
    if len(sys.argv) != 2:
        print("Usage: python3 parser.py <map_file_path>")
        sys.exit(1)
    return sys.argv[1]


if __name__ == "__main__":
    path = get_file_path()
    try:
        graph = Parser(path).parse()
    except (ParseError, FileNotFoundError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    print(f"nb_drones : {graph.nb_drones}")
    print(f"start     : {graph.start.name}")
    print(f"end       : {graph.end.name}")
    print(f"\nZones ({len(graph.zones)}):")
    for zone in graph.zones.values():
        print(f"  {zone}")
    print(f"\nConnections ({len(graph.connections)}):")
    for conn in graph.connections:
        print(f"  {conn}")

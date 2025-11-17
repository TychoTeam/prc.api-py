from typing import Optional, Literal, TYPE_CHECKING, cast, List
from ..player import Player

if TYPE_CHECKING:
    from prc.api_types.v1 import v1_ServerVehicle
    from prc.server import Server
    from .player import ServerPlayer


class VehicleOwner:
    """
    Represents a server vehicle owner partial player.

    Parameters
    ----------
    server
        The server handler.
    name
        The player name.
    """

    def __init__(self, server: "Server", name: str):
        self._server = server

        self.name = str(name)

    @property
    def player(self) -> Optional["ServerPlayer"]:
        """
        The full server player, if found.
        """

        return self._server._get_player(name=self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, VehicleOwner) or isinstance(other, Player):
            return self.name == other.name
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"


class VehicleTexture:
    """
    Represents a server vehicle texture or livery.

    Parameters
    ----------
    name
        The vehicle texture's name.
    """

    def __init__(self, name: str):
        self.name = name

    def is_default(self) -> bool:
        """
        Whether this texture is **LIKELY** a default game texture and **NOT** a custom texture (aka. custom livery).
        """

        return self.name in _default_textures

    def __eq__(self, other: object) -> bool:
        if isinstance(other, VehicleTexture):
            return self.name == other.name
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"


class Vehicle:
    """
    Represents a currently spawned server vehicle.

    Parameters
    ----------
    server
        The server handler.
    data
        The response data.
    """

    def __init__(self, server: "Server", data: "v1_ServerVehicle"):
        self._server = server

        self.owner = VehicleOwner(server, data.get("Owner"))
        self.texture = VehicleTexture(name=data.get("Texture") or "Standard")

        self.model: VehicleModel = cast(VehicleModel, data.get("Name"))
        self.year: Optional[int] = None

        parsed_name = self.model.split(" ")
        for i in [0, -1]:
            if parsed_name[i].isdigit() and len(parsed_name[i]) == 4:
                self.year = int(parsed_name.pop(i))
                self.model = cast(VehicleModel, " ".join(parsed_name))

        for i, v in enumerate(server._server_cache.vehicles.items()):
            if v.owner == self.owner and v.is_secondary() == self.is_secondary():
                server._server_cache.vehicles.remove(i)
        server._server_cache.vehicles.add(self)

    @property
    def full_name(self) -> "VehicleName":
        """
        The vehicle model name suffixed by the model year (if applicable). Unique for each *game* vehicle. A *server* may have multiple spawned vehicles with the same full name.
        """

        return cast(VehicleName, f"{self.year or ''} {self.model}".strip())

    def is_secondary(self) -> bool:
        """
        Whether this is the vehicle owner's secondary vehicle. Secondary vehicles include ATVs, UTVs, the lawn mower and such.
        """

        return self.full_name in _secondary_vehicles

    def is_prestige(self) -> bool:
        """
        Whether this vehicle model is considered a prestige vehicle (aka. exotic vehicle).
        """

        return self.model in _prestige_vehicles

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Vehicle):
            return self.full_name == other.full_name and self.owner == other.owner
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.full_name}, owner={self.owner.name}>"


# All vehicle names
VehicleName = Literal[
    # CIV
    "1977 Arrow Phoenix Nationals",
    "2024 Averon Anodic",
    "2023 Averon Bremen VS Garde",
    "2022 Averon Q8",
    "2017 Averon R8",
    "2020 Averon RS3",
    "2010 Averon S5",
    "2020 BKM Munich",
    "2020 BKM Risen Roadster",
    "2009 Bullhorn BH15",
    "2022 Bullhorn Determinator SFP Blackjack Widebody",
    "2022 Bullhorn Determinator SFP Fury Blackjack Widebody",
    "2022 Bullhorn Determinator SFP Fury",
    "2022 Bullhorn Determinator C/T",
    "2008 Bullhorn Determinator",
    "1988 Bullhorn Foreman",
    "2020 Bullhorn Prancer Widebody",
    "1969 Bullhorn Prancer",
    "1969 Bullhorn Prancer Colonel Fields",
    "1969 Bullhorn Prancer Talladega",
    "2011 Bullhorn Prancer",
    "2015 Bullhorn Prancer",
    "2018 Bullhorn Pueblo",
    "2024 Celestial Truckatron",
    "2023 Celestial Type-6",
    "2016 Chevlon Amigo LZR",
    "2016 Chevlon Amigo S",
    "2011 Chevlon Amigo ZL1",
    "2011 Chevlon Amigo S",
    "1994 Chevlon Antelope",
    "2002 Chevlon Camion",
    "2008 Chevlon Camion",
    "2018 Chevlon Camion",
    "2021 Chevlon Camion",
    "1992 Chevlon Captain",
    "2009 Chevlon Captain",
    "1994 Chevlon Captain LTZ",
    "2006 Chevlon Commuter Van",
    "2014 Chevlon Corbeta 1M Edition",
    "2023 Chevlon Corbeta 8",
    "1967 Chevlon Corbeta C2",
    "2014 Chevlon Corbeta RZR",
    "2014 Chevlon Corbeta X08",
    "1981 Chevlon Inferno",
    "2007 Chevlon Landslide",
    "1981 Chevlon L/15",
    "1981 Chevlon L/15 Side Step",
    "1981 Chevlon L/35 Extended",
    "2019 Chevlon Platoro",
    "2005 Chevlon Revver",
    "2005 Chryslus Champion",
    "2014 Elysion Slick",
    "1956 Falcon Advance 100 Holiday Edition",
    "1956 Falcon Advance 100",
    "2020 Falcon Advance 450 Royal Ranch",
    "2020 Falcon Advance 450",
    "1934 Falcon Coupe",
    "1934 Falcon Coupe Hotrod",
    "2024 Falcon eStallion",
    "2021 Falcon Heritage",
    "2022 Falcon Heritage Track",
    "2021 Falcon Rampage Beast",
    "2021 Falcon Rampage Bigfoot 2-Door",
    "2016 Falcon Scavenger",
    "1969 Falcon Stallion 350",
    "2015 Falcon Stallion 350",
    "2003 Falcon Traveller",
    "2022 Ferdinand Jalapeno Turbo",
    "2020 Ferrari F8 Tributo",
    "2023 Kovac Heladera",
    "1995 Leland Birchwood Hearse",
    "2010 Leland LTS",
    "2023 Leland LTS5-V Blackwing",
    "1959 Leland Series 67 Skyview",
    "2020 Leland Vault",
    "Lawn Mower",
    "2022 Navara Boundary",
    "2013 Navara Horizon",
    "2020 Navara Imperium",
    "2020 Overland Apache SFP",
    "1995 Overland Apache",
    "2011 Overland Apache",
    "2018 Overland Buckaroo",
    "2025 Pea Car",
    "1968 Sentinel Platinum",
    "2011 Silhouette Carbon",
    "2020 Strugatti Ettore",
    "2021 Stuttgart Executive",
    "2022 Stuttgart Landschaft",
    "2021 Stuttgart Vierturig",
    "2022 Sumo Reflexion",
    "2016 Surrey 650S",
    "2021 Takeo Experience",
    "2022 Terrain Traveller",
    "2023 Vellfire Everest VRD Max",
    "1995 Vellfire Evertt Extended Cab",
    "2019 Vellfire Pioneer",
    "2022 Vellfire Prairie",
    "2009 Vellfire Prima",
    "2020 Vellfire Riptide",
    "1984 Vellfire Runabout",
    # CIV JOBS
    "Bank Truck",
    "Dump Truck",
    "2013 Falcon Scavenger Security",
    "2020 Falcon Scavenger Taxi",
    "Farm Tractor 5100M",
    "Forklift",
    "Front Loader Tractor",
    "Front-Loader Garbage Truck",
    "Fuel Tanker",
    "Garbage Truck",
    "La Mesa Food Truck",
    "2018 Leland Limo",
    "Mail Truck",
    "Mail Van",
    "Metro Transit Bus",
    "News Van",
    "Shuttle Bus",
    "Three Guys Food Truck",
    # COMMON
    "4-Wheeler",
    "Canyon Descender",
    # LEO
    "2022 Averon Q8",
    "2020 BKM Munich",
    "2009 Bullhorn BH15 SSV",
    "2022 Bullhorn Determinator SFP Fury",
    "1988 Bullhorn Foreman",
    "2020 Bullhorn Prancer Pursuit Widebody",
    "2011 Bullhorn Prancer Pursuit",
    "2015 Bullhorn Prancer Pursuit",
    "2018 Bullhorn Pueblo Pursuit",
    "2024 Celestial Truckatron",
    "2011 Chevlon Amigo LZR",
    "1994 Chevlon Antelope SS",
    "2000 Chevlon Camion PPV",
    "2008 Chevlon Camion PPV",
    "2018 Chevlon Camion PPV",
    "2021 Chevlon Camion PPV",
    "2009 Chevlon Captain PPV",
    "2006 Chevlon Commuter Van",
    "2014 Chevlon Corbeta RZR",
    "1981 Chevlon Inferno",
    "2019 Chevlon Platoro PPV",
    "2020 Emergency Services Falcon Advance+",
    "2024 Falcon eStallion",
    "2019 Falcon Interceptor Utility",
    "2021 Falcon Rampage PPV",
    "2015 Falcon Stallion 350",
    "2002 Falcon Traveller",
    "2005 Mobile Command",
    "Prisoner Transport Bus",  # SHERIFF ONLY
    "2020 Stuttgart Runner",
    "2011 SWAT Armored Truck",
    # FD
    "2020 Brush Falcon Advance+",
    "2022 Bullhorn Pueblo Pursuit",
    "2018 Chevlon Camion",
    "2020 Falcon Advance 350",
    "2020 Falcon Advance 450 Ambulance",
    "Heavy Rescue",
    "Heavy Tanker",
    "International Ambulance",
    "Ladder Truck",
    "Medical Bus",
    "Mobile Command Center",
    "Paramedic SUV",
    "Redline Fire Engine",
    "2020 Squad Falcon Advance+",
    "Special Operations Unit",
    "Tanker",
    # DOT
    "2019 Chevlon Platoro Utility",
    "Cone Truck",
    "2020 Falcon Advance+ Roadside Assist",
    "2020 Falcon Advance+ Tow Truck",
    "Flatbed Tow Truck",
    "Street Sweeper",
    "Salt Truck",
    "1995 Vellfire Evertt Crew Cab",
]

# Unique vehicle models
VehicleModel = Literal[
    "4-Wheeler",
    "Arrow Phoenix Nationals",
    "Averon Anodic",
    "Averon Bremen VS Garde",
    "Averon Q8",
    "Averon R8",
    "Averon RS3",
    "Averon S5",
    "BKM Munich",
    "BKM Risen Roadster",
    "Bank Truck",
    "Brush Falcon Advance+",
    "Bullhorn BH15 SSV",
    "Bullhorn BH15",
    "Bullhorn Determinator SFP Blackjack Widebody",
    "Bullhorn Determinator SFP Fury",
    "Bullhorn Determinator",
    "Bullhorn Foreman",
    "Bullhorn Prancer Colonel Fields",
    "Bullhorn Prancer Pursuit Widebody",
    "Bullhorn Prancer Pursuit",
    "Bullhorn Prancer Talladega",
    "Bullhorn Prancer Widebody",
    "Bullhorn Prancer",
    "Bullhorn Pueblo Pursuit",
    "Bullhorn Pueblo",
    "Canyon Descender",
    "Celestial Truckatron",
    "Celestial Type-6",
    "Chevlon Amigo LZR",
    "Chevlon Amigo S",
    "Chevlon Amigo ZL1",
    "Chevlon Antelope SS",
    "Chevlon Antelope",
    "Chevlon Camion PPV",
    "Chevlon Camion",
    "Chevlon Captain LTZ",
    "Chevlon Captain PPV",
    "Chevlon Captain",
    "Chevlon Commuter Van",
    "Chevlon Corbeta 1M Edition",
    "Chevlon Corbeta 8",
    "Chevlon Corbeta C2",
    "Chevlon Corbeta RZR",
    "Chevlon Corbeta X08",
    "Chevlon Inferno",
    "Chevlon L/15 Side Step",
    "Chevlon L/15",
    "Chevlon L/35 Extended",
    "Chevlon Landslide",
    "Chevlon Platoro PPV",
    "Chevlon Platoro Utility",
    "Chevlon Platoro",
    "Chevlon Revver",
    "Chryslus Champion",
    "Cone Truck",
    "Dump Truck",
    "Elysion Slick",
    "Emergency Services Falcon Advance+",
    "Falcon Advance 100 Holiday Edition",
    "Falcon Advance 450 Royal Ranch",
    "Falcon Advance 450",
    "Falcon Advance+ Roadside Assist",
    "Falcon Advance+ Tow Truck",
    "Falcon Coupe",
    "Falcon Coupe Hotrod",
    "Falcon Heritage Track",
    "Falcon Heritage",
    "Falcon Interceptor Utility",
    "Falcon Rampage Beast",
    "Falcon Rampage Bigfoot 2-Door",
    "Falcon Rampage PPV",
    "Falcon Scavenger Security",
    "Falcon Scavenger Taxi",
    "Falcon Scavenger",
    "Falcon Stallion 350",
    "Falcon Traveller",
    "Falcon eStallion",
    "Farm Tractor 5100M",
    "Ferdinand Jalapeno Turbo",
    "Ferrari F8 Tributo",
    "Fire Engine",
    "Flatbed Tow Truck",
    "Forklift",
    "Front Loader Tractor",
    "Front-Loader Garbage Truck",
    "Fuel Tanker",
    "Garbage Truck",
    "Heavy Rescue",
    "Heavy Tanker",
    "International Ambulance",
    "Kovac Heladera",
    "La Mesa Food Truck",
    "Ladder Truck",
    "Lawn Mower",
    "Leland Birchwood Hearse",
    "Leland LTS",
    "Leland LTS5-V Blackwing",
    "Leland Limo",
    "Leland Series 67 Skyview",
    "Leland Vault",
    "Mail Truck",
    "Mail Van",
    "Medical Bus",
    "Metro Transit Bus",
    "Mobile Command Center",
    "Mobile Command",
    "Navara Boundary",
    "Navara Horizon",
    "Navara Imperium",
    "News Van",
    "Overland Apache SFP",
    "Overland Apache",
    "Overland Buckaroo",
    "Paramedic SUV",
    "Pea Car",
    "Prisoner Transport Bus",
    "Stuttgart Runner",
    "SWAT Truck",
    "Salt Truck",
    "Sentinel Platinum",
    "Shuttle Bus",
    "Silhouette Carbon",
    "Special Operations Unit",
    "Squad Falcon Advance+",
    "Street Sweeper",
    "Strugatti Ettore",
    "Stuttgart Executive",
    "Stuttgart Landschaft",
    "Stuttgart Vierturig",
    "Sumo Reflexion",
    "Surrey 650S",
    "Takeo Experience",
    "Tanker",
    "Terrain Traveller",
    "Three Guys Food Truck",
    "Vellfire Everest VRD Max",
    "Vellfire Evertt Crew Cab",
    "Vellfire Evertt Extended Cab",
    "Vellfire Pioneer",
    "Vellfire Prairie",
    "Vellfire Prima",
    "Vellfire Riptide",
    "Vellfire Runabout",
]

_secondary_vehicles: List[VehicleName] = [
    "4-Wheeler",
    "Canyon Descender",
    "Lawn Mower",
]

_prestige_vehicles: List[VehicleModel] = [
    "Averon Q8",
    "Averon R8",
    "Averon RS3",
    "Averon S5",
    "BKM Munich",
    "Chevlon Corbeta 1M Edition",
    "Chevlon Corbeta 8",
    "Chevlon Corbeta RZR",
    "Chevlon Corbeta X08",
    "Falcon Heritage Track",
    "Falcon Heritage",
    "Ferdinand Jalapeno Turbo",
    "Ferrari F8 Tributo",
    "Leland LTS5-V Blackwing",
    "Leland Vault",
    "Silhouette Carbon",
    "Strugatti Ettore",
    "Stuttgart Vierturig",
    "Surrey 650S",
    "Takeo Experience",
    "Terrain Traveller",
]

_default_textures = [
    "Standard",
    "Ghost",
    "Undercover",
    "SWAT",
    "Supervisor",
]

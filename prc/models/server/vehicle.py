from typing import Optional, Literal, TYPE_CHECKING, Dict, cast, List

if TYPE_CHECKING:
    from prc.server import Server


class VehicleOwner:
    """Represents a server vehicle owner partial player."""

    def __init__(self, server: "Server", name: str):
        self._server = server

        self.name = str(name)

    @property
    def player(self):
        """The full server player, if found."""
        return self._server._get_player(name=self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, VehicleOwner):
            return self.name == other.name
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"


class VehicleTexture:
    """Represents a server vehicle texture or livery."""

    def __init__(self, name: str):
        self.name = name

    def is_default(self) -> bool:
        """Whether this texture is likely a default game texture."""
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
    """Represents a currently spawned server vehicle."""

    def __init__(self, server: "Server", data: Dict):
        self._server = server

        self.owner = VehicleOwner(server, data.get("Owner"))  # type: ignore
        texture = data.get("Texture")
        self.texture = VehicleTexture(name=texture) if texture else None

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
        """The vehicle model name suffixed by the model year (if applicable). Unique for each *game* vehicle, while a *server* may have multiple spawned vehicles with the same full name."""
        return cast(VehicleName, f"{self.year or ''} {self.model}".strip())

    def is_secondary(self) -> bool:
        """Whether this is the vehicle owner's secondary vehicle. Secondary vehicles include ATVs, UTVs, the lawn mower and such."""
        return self.full_name in _secondary_vehicles

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Vehicle):
            return self.full_name == other.full_name and self.owner == other.owner
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.full_name}>"


# All vehicle names
VehicleName = Literal[
    # CIV
    "1934 Falcon Coupe Hotrod",
    "1956 Falcon Advance 100 Holiday Edition",
    "1994 Chevlon Antelope",
    "2021 Stuttgart Executive",
    "1988 Bullhorn Foreman",
    "2016 Chevlon Amigo LZR",
    "1995 Leland Birchwood Hearse",
    "Lawn Mower",
    "2025 Pea Car",
    "2003 Falcon Prime Eques",
    "2002 Chevlon Camion",
    "1995 Overland Apache",
    "2009 Chevlon Captain",
    "2002 Falcon Traveller",
    "2003 Falcon Traveller",
    "1995 Vellfire Evertt",
    "1981 Chevlon L/15",
    "2009 Vellfire Prima",
    "2014 Elysion Slick",
    "2007 Chevlon Landslide",
    "1981 Chevlon Inferno",
    "2020 Navara Imperium",
    "1981 Chevlon L/35 Extended",
    "2006 Chevlon Commuter Van",
    "2010 Leland LTS",
    "2008 Chevlon Camion",
    "1967 Chevlon Corbeta C2",
    "2009 Bullhorn BH15",
    "1968 Sentinel Platinum",
    "2015 Falcon Fission",
    "2024 Falcon eStallion",
    "2018 Chevlon Camion",
    "2018 Falcon Advance",
    "1984 Vellfire Runabout",
    "2016 Falcon Scavenger",
    "2005 Chevlon Revver",
    "2011 Overland Apache",
    "2018 Overland Buckaroo",
    "2005 Chryslus Champion",
    "2020 Vellfire Riptide",
    "2011 Bullhorn Prancer",
    "2022 Navara Boundary",
    "2023 Celestial Type-6",
    "1977 Arrow Phoenix Nationals",
    "2015 Bullhorn Prancer",
    "1969 Bullhorn Prancer",
    "2008 Bullhorn Determinator",
    "2021 Chevlon Camion",
    "1969 Falcon Stallion 350",
    "2024 Falcon eStallion",
    "2016 Chevlon Amigo Sport",
    "2011 Chevlon Amigo ZL1",
    "2019 Chevlon Platoro",
    "2022 Vellfire Prairie",
    "2024 Falcon Advance Bolt",
    "2021 Falcon Rampage Bigfoot 2-Door",
    "2024 Averon Anodic",
    "2018 Bullhorn Pueblo",
    "2022 Falcon Traveller",
    "2017 Falcon Advance Beast",
    "2020 Overland Apache SFP",
    "2022 Bullhorn Determinator SFP Fury",
    "2022 Falcon Advance",
    "2020 Bullhorn Prancer Widebody",
    "2020 Leland Vault",
    "2022 Bullhorn Determinator SFP Blackjack Widebody",
    "2021 Falcon Rampage Beast",
    "2010 Averon S5",
    "2015 Falcon Stallion 350",
    "2022 Ferdinand Jalapeno Turbo",
    "2020 BKM Munich",
    "2022 Terrain Traveller",
    "2021 Stuttgart Vierturig",
    "2020 BKM Risen Roadster",
    "2020 Averon RS3",
    "2024 Celestial Truckatron",
    "2022 Averon Q8",
    "2013 Navara Horizon",
    "2019 Vellfire Pioneer",
    "2022 Stuttgart Landschaft",
    "2023 Leland LTS5-V Blackwing",
    "2014 Chevlon Corbeta TZ",
    "2023 Chevlon Corbeta 8",
    "2021 Takeo Experience",
    "2021 Falcon Heritage",
    "2017 Averon R8",
    "2016 Surrey 650S",
    "2020 Strugatti Ettore",
    "2023 Vellfire Everest VRD Max",
    # CIV JOBS
    "2003 Falcon Prime Eques Taxi",
    "2020 Falcon Scavenger Taxi",
    "2018 Leland Limo",
    "Shuttle Bus",
    "Metro Transit Bus",
    "Farm Tractor 5100M",
    "Mail Truck",
    "Mail Van",
    "Fuel Tanker",
    "News Van",
    "Garbage Truck",
    "Front-Loader Garbage Truck",
    "Three Guys Food Truck",
    "La Mesa Food Truck",
    "2013 Falcon Scavenger Security",
    "Bank Truck",
    "Front Loader Tractor",
    "Dump Truck",
    "Forklift",
    # COMMON
    "Canyon Descender",
    "4-Wheeler",
    # LEO
    "2003 Falcon Prime Eques",
    "2006 Chevlon Captain PPV",
    "2018 Bullhorn Pueblo Pursuit",
    "2011 Chevlon Amigo LZR",
    "2000 Chevlon Camion PPV",
    "2008 Chevlon Camion PPV",
    "2018 Chevlon Camion PPV",
    "2021 Chevlon Camion PPV",
    "2024 Celestial Truckatron",
    "2017 Falcon Interceptor Sedan",
    "2011 Bullhorn Prancer Pursuit",
    "2018 Falcon Advance SSV",
    "2009 Bullhorn BH15 SSV",
    "2015 Falcon Stallion 350",
    "2024 Falcon Advance Bolt",
    "2020 BKM Munich",
    "2021 Falcon Rampage PPV",
    "2022 Falcon Traveller SSV",
    "2006 Chevlon Commuter Van",
    "2011 SWAT Truck",
    "2019 Chevlon Platoro PPV",
    "2015 Bullhorn Prancer Pursuit",
    "2020 Bullhorn Prancer Pursuit Widebody",
    "2014 Chevlon Corbeta TZ",
    "2013 Falcon Interceptor Utility",
    "2019 Falcon Interceptor Utility",
    "2020 Falcon Interceptor Utility",
    "2022 Bullhorn Determinator SFP Fury",
    "2022 Averon Q8",
    "2020 Emergency Services Falcon Advance+",
    "2005 Mobile Command",
    "Prisoner Transport Bus",  # SHERIFF ONLY
    "1981 Chevlon Inferno",
    "1988 Bullhorn Foreman",
    "2020 Stuttgart Runner",
    # FD
    "Fire Engine",
    "Tanker",
    "Heavy Tanker",
    "Ladder Truck",
    "Heavy Rescue",
    "Special Operations Unit",
    "Bullhorn Ambulance",
    "International Ambulance",
    "Paramedic SUV",
    "Medical Bus",
    "2021 Utility Falcon Advance+",
    "2020 Squad Falcon Advance+",
    "2020 Brush Falcon Advance+",
    "2018 Falcon Advance",
    "2015 Bullhorn Prancer",
    "2018 Chevlon Camion",
    "Mobile Command Center",
    # DOT
    "1995 Vellfire Evertt Crew Cab",
    "Flatbed Tow Truck",
    "2019 Falcon Advance+ Utility",
    "2020 Falcon Advance+ Tow Truck",
    "Cone Truck",
    "2020 Falcon Advance+ Roadside Assist",
    "Street Sweeper",
    "Salt Truck",
    "2019 Chevlon Platoro Utility",
]

# Unique vehicle models
VehicleModel = Literal[
    # Civilian and Common
    "Falcon Coupe Hotrod",
    "Falcon Advance 100 Holiday Edition",
    "Chevlon Antelope",
    "Stuttgart Executive",
    "Bullhorn Foreman",
    "Chevlon Amigo LZR",
    "Leland Birchwood Hearse",
    "Lawn Mower",
    "Pea Car",
    "Falcon Prime Eques",
    "Chevlon Camion",
    "Overland Apache",
    "Chevlon Captain",
    "Falcon Traveller",
    "Vellfire Evertt",
    "Chevlon L/15",
    "Vellfire Prima",
    "Elysion Slick",
    "Chevlon Landslide",
    "Chevlon Inferno",
    "Navara Imperium",
    "Chevlon L/35 Extended",
    "Chevlon Commuter Van",
    "Leland LTS",
    "Chevlon Corbeta C2",
    "Bullhorn BH15",
    "Sentinel Platinum",
    "Falcon Fission",
    "Falcon Advance",
    "Vellfire Runabout",
    "Falcon Scavenger",
    "Chevlon Revver",
    "Overland Buckaroo",
    "Chryslus Champion",
    "Vellfire Riptide",
    "Bullhorn Prancer",
    "Navara Boundary",
    "Celestial Type-6",
    "Arrow Phoenix Nationals",
    "Bullhorn Determinator",
    "Falcon Stallion 350",
    "Falcon eStallion",
    "Chevlon Amigo Sport",
    "Chevlon Amigo ZL1",
    "Chevlon Platoro",
    "Vellfire Prairie",
    "Falcon Advance Bolt",
    "Falcon Rampage Bigfoot 2-Door",
    "Averon Anodic",
    "Bullhorn Pueblo",
    "Falcon Advance Beast",
    "Overland Apache SFP",
    "Bullhorn Determinator SFP Fury",
    "Bullhorn Prancer Widebody",
    "Leland Vault",
    "Bullhorn Determinator SFP Blackjack Widebody",
    "Falcon Rampage Beast",
    "Averon S5",
    "Ferdinand Jalapeno Turbo",
    "BKM Munich",
    "Terrain Traveller",
    "Stuttgart Vierturig",
    "BKM Risen Roadster",
    "Averon RS3",
    "Celestial Truckatron",
    "Averon Q8",
    "Navara Horizon",
    "Vellfire Pioneer",
    "Stuttgart Landschaft",
    "Leland LTS5-V Blackwing",
    "Chevlon Corbeta TZ",
    "Chevlon Corbeta 8",
    "Takeo Experience",
    "Falcon Heritage",
    "Averon R8",
    "Surrey 650S",
    "Strugatti Ettore",
    "Vellfire Everest VRD Max",
    "Falcon Prime Eques Taxi",
    "Falcon Scavenger Taxi",
    "Leland Limo",
    "Shuttle Bus",
    "Metro Transit Bus",
    "Farm Tractor 5100M",
    "Mail Truck",
    "Mail Van",
    "Fuel Tanker",
    "News Van",
    "Garbage Truck",
    "Front-Loader Garbage Truck",
    "Three Guys Food Truck",
    "La Mesa Food Truck",
    "Falcon Scavenger Security",
    "Bank Truck",
    "Front Loader Tractor",
    "Dump Truck",
    "Forklift",
    "Canyon Descender",
    "4-Wheeler",
    # LEO only
    "Chevlon Captain PPV",
    "Bullhorn Pueblo Pursuit",
    "Chevlon Camion PPV",
    "Falcon Interceptor Sedan",
    "Bullhorn Prancer Pursuit",
    "Falcon Advance SSV",
    "Bullhorn BH15 SSV",
    "Falcon Rampage PPV",
    "Falcon Traveller SSV",
    "SWAT Truck",
    "Chevlon Platoro PPV",
    "Bullhorn Prancer Pursuit Widebody",
    "Falcon Interceptor Utility",
    "Emergency Services Falcon Advance+",
    "Mobile Command",
    "Prisoner Transport Bus",
    "Stuttgart Runner",
    # FD only
    "Fire Engine",
    "Tanker",
    "Heavy Tanker",
    "Ladder Truck",
    "Heavy Rescue",
    "Special Operations Unit",
    "Bullhorn Ambulance",
    "International Ambulance",
    "Paramedic SUV",
    "Medical Bus",
    "Utility Falcon Advance+",
    "Squad Falcon Advance+",
    "Brush Falcon Advance+",
    "Mobile Command Center",
    # DOT only
    "Vellfire Evertt Crew Cab",
    "Flatbed Tow Truck",
    "Falcon Advance+ Utility",
    "Falcon Advance+ Tow Truck",
    "Cone Truck",
    "Falcon Advance+ Roadside Assist",
    "Street Sweeper",
    "Salt Truck",
    "Chevlon Platoro Utility",
]

_secondary_vehicles: List[VehicleName] = [
    "Lawn Mower",
    "4-Wheeler",
    "Canyon Descender",
]

_default_textures = ["Standard", "Ghost", "Undercover", "SWAT"]

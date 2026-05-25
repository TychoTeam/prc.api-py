from typing import Optional, Literal, TYPE_CHECKING, cast, List

from .player import PartialServerPlayer

if TYPE_CHECKING:
    from prc.api_types.v2 import v2_ServerVehicle
    from prc.server import Server


class VehicleOwner(PartialServerPlayer):
    """
    Represents a server vehicle owner partial player.

    Parameters
    ----------
    server
        The server handler.
    name
        The player name.
    """

    name: str

    def __init__(self, server: "Server", name: str):
        self._server = server

        self.name = str(name)

        super().__init__(server, value=self.name)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"


class VehicleColor:
    """
    Represents a server vehicle color.

    Parameters
    ----------
    name
        The color name.
    hex
        The color HEX code formatted as `#ffffff`.
    """

    name: str
    hex: str
    value: int

    def __init__(self, name: str, hex: str):
        self.name = name
        self.hex = hex.lower()

        self.value = int(self.hex.replace("#", ""), 16)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, VehicleTexture) and self.name == other.name

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        return self.hex

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

    name: str

    def __init__(self, name: str):
        self.name = name

    def is_default(self) -> bool:
        """
        Whether this texture is **LIKELY** a default game texture and **NOT** a custom texture (aka. custom livery). Default game textures include **ALL** non-custom textures/liveries.
        """

        return self.name in _default_textures

    def is_custom(self) -> bool:
        """
        Whether this texture is **LIKELY** a custom livery.
        """

        return not self.is_default

    def is_fictional(self) -> bool:
        """
        Whether this texture is **LIKELY** a fictional game texture. Fictional textures include most in-game textures that have fictional text.
        """

        return self.name in _fictional_textures

    def __eq__(self, other: object) -> bool:
        return isinstance(other, VehicleTexture) and self.name == other.name

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        return self.name

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

    owner: VehicleOwner
    texture: VehicleTexture
    color: Optional[VehicleColor]
    model: "VehicleModel"
    year: Optional[int] = None
    plate: str

    def __init__(self, server: "Server", data: "v2_ServerVehicle"):
        self._server = server

        self.owner = VehicleOwner(server, data["Owner"])
        self.texture = VehicleTexture(name=data.get("Texture", None) or "Standard")
        self.plate = data["Plate"]

        self.color = None
        if (color_name := data.get("ColorName")) and (
            color_hex := data.get("ColorHex")
        ):
            self.color = VehicleColor(name=color_name, hex=color_hex)

        self.model = cast(VehicleModel, data["Name"])

        parsed_name = self.model.split(" ")
        for i in [0, -1]:
            if parsed_name[i].isdigit() and len(parsed_name[i]) == 4:
                year = int(parsed_name.pop(i))
                if 2100 >= year >= 1900:
                    self.year = year
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
        return (
            isinstance(other, Vehicle)
            and (self.full_name == other.full_name)
            and (self.owner == other.owner)
        )

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.full_name}, owner={self.owner.name}, color={self.color}, texture={self.texture}, plate={self.plate}>"


class VehicleList(List[Vehicle]):
    def copy(self):
        return VehicleList(self)

    def get_prestige(self) -> "VehicleList":
        """
        Find all spawned prestige vehicles (aka. exotic vehicles).
        """

        return VehicleList(v for v in self if v.is_prestige())

    def get_primary(self) -> "VehicleList":
        """
        Find all spawned primary vehicles.
        """

        return VehicleList(v for v in self if not v.is_secondary())

    def get_secondary(self) -> "VehicleList":
        """
        Find all spawned secondary vehicles.
        """

        return VehicleList(v for v in self if v.is_secondary())

    def with_default_texture(self) -> "VehicleList":
        """
        Find all spawned vehicles with a texture that is **LIKELY** a default game texture and **NOT** a custom texture (aka. custom livery). Default game textures include **ALL** non-custom textures/liveries.
        """

        return VehicleList(v for v in self if v.texture.is_default())

    def with_fictional_texture(self) -> "VehicleList":
        """
        Find all spawned vehicles with a texture that is **LIKELY** a fictional game texture. Fictional textures include most in-game textures that have fictional text.
        """

        return VehicleList(v for v in self if v.texture.is_fictional())

    def by_texture(self, texture: str, /) -> "VehicleList":
        """
        Find all spawned vehicles with this texture set (case insensitive).
        """

        return VehicleList(
            v for v in self if v.texture.name.lower() == texture.lower().strip()
        )

    def by_name(self, name: "VehicleName", /) -> "VehicleList":
        """
        Find all spawned vehicles of this exact full name.
        """

        return VehicleList(v for v in self if v.full_name == name)

    def by_model(self, model: "VehicleModel", /) -> "VehicleList":
        """
        Find all spawned vehicles of this model.
        """

        return VehicleList(v for v in self if v.model == model)

    def by_owner(self, *, name: str) -> "VehicleList":
        """
        Find all spawned vehicles owned by a player using their username. A player may have up to 2 vehicles (1 primary, 1 secondary).
        """

        return VehicleList(
            v for v in self if v.owner.name.lower() == name.lower().strip()
        )

    def by_plate(self, plate: str, /) -> "VehicleList":
        """
        Find all spawned vehicles with a certain plate (likely same owner). Plates are case insensitive and are always capitalized.
        """

        return VehicleList(v for v in self if v.plate == plate.upper().strip())

    def find_plate(self, keyword: str, /) -> "VehicleList":
        """
        Find all spawned vehicles with a plate containing a certain keyword. Plates and keywords are case insensitive and are always capitalized.
        """

        return VehicleList(v for v in self if keyword.upper().strip() in v.plate)


# All vehicle names
VehicleName = Literal[
    # CIV
    "1977 Arrow Phoenix Nationals",
    "2024 Averon Anodic",
    "2023 Averon Bremen VS Garde",
    "2020 Averon LM R",
    "2020 Averon LM",
    "2022 Averon Q8",
    "2020 Averon RS3",
    "2010 Averon S5",
    "2020 BKM Munich",
    "2020 BKM Risen Roadster",
    "2009 Bullhorn BH15",
    "2022 Bullhorn Determinator SFP Fury Blackjack Widebody",
    "2022 Bullhorn Determinator SFP Fury",
    "2022 Bullhorn Determinator C/T",
    "2008 Bullhorn Determinator",
    "1988 Bullhorn Foreman",
    "1969 Bullhorn Prancer Colonel Fields",
    "2020 Bullhorn Prancer C/T",
    "2020 Bullhorn Prancer Fury Widebody",
    "2011 Bullhorn Prancer S",
    "1969 Bullhorn Prancer Talladega",
    "1969 Bullhorn Prancer",
    "2022 Bullhorn Pueblo V6",
    "2022 Bullhorn Pueblo SFP Fury",
    "2024 Celestial Truckatron",
    "2022 Celestial Type-5",
    "2024 Celestial Type-6",
    "2022 Celestial Type-7",
    "2016 Chevlon Amigo LZR",
    "2016 Chevlon Amigo S",
    "2011 Chevlon Amigo ZL1",
    "2011 Chevlon Amigo S",
    "1994 Chevlon Antelope",
    "2002 Chevlon Camion GMT 800 LTS",
    "2002 Chevlon Camion GMT 800 LT",
    "2002 Chevlon Camion GMT 800 S",
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
    "2020 Falcon Advance 350 Royal Ranch",
    "2020 Falcon Advance 350",
    "2020 Falcon Advance 450 Royal Ranch",
    "2020 Falcon Advance 450",
    "2017 Falcon Aquarius STP",
    "1934 Falcon Coupe",
    "1934 Falcon Coupe Hotrod",
    "2024 Falcon eStallion",
    "2021 Falcon Heritage",
    "2022 Falcon Heritage Track",
    "2003 Falcon Prime Eques",
    "2021 Falcon Rampage Beast",
    "2021 Falcon Rampage Bigfoot 2-Door",
    "2021 Falcon Rampage Prairie",
    "2024 Falcon Scavenger Royal Ranch",
    "2013 Falcon Scavenger",
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
    "2019 Vellfire Pioneer Targa",
    "2019 Vellfire Pioneer",
    "2022 Vellfire Prairie",
    "2009 Vellfire Prima",
    "2020 Vellfire Riptide",
    "1984 Vellfire Runabout",
    # CIV JOBS
    "Bank Truck",
    "2003 Falcon Prime Eques Taxi",
    "2013 Falcon Scavenger Security",
    "2024 Falcon Scavenger Taxi",
    "Farm Tractor 5100M",
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
    "2022 Bullhorn Determinator C/T",
    "2022 Bullhorn Determinator SFP Fury Blackjack Widebody",
    "2022 Bullhorn Determinator SFP Fury",
    "1988 Bullhorn Foreman",
    "2020 Bullhorn Prancer Fury Widebody Pursuit",
    "1969 Bullhorn Prancer HotRod",
    "2011 Bullhorn Prancer Pursuit",
    "2015 Bullhorn Prancer Pursuit",
    "2022 Bullhorn Pueblo Pursuit",
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
    "2020 Falcon Advance 350",
    "2022 Falcon Advance XET",
    "2024 Falcon eStallion",
    "2018 Falcon Global 350",
    "2017 Falcon Interceptor Sedan",
    "2013 Falcon Interceptor Utility",
    "2019 Falcon Interceptor Utility",
    "2024 Falcon Interceptor Utility",
    "2003 Falcon Prime Eques Interceptor",
    "2021 Falcon Rampage Interceptor",
    "2015 Falcon Stallion 350",
    "2022 Falcon Traveller PPV",
    "2002 Falcon Traveller",
    "2005 Mobile Command",
    "Prisoner Transport Bus",  # SHERIFF ONLY
    "2020 Stuttgart Runner Prisoner Transport",
    "2011 SWAT Armored Truck",
    # FD
    "2020 Brush Falcon Advance+",
    "2022 Bullhorn Pueblo Pursuit",
    "2018 Chevlon Camion",
    "1981 Chevlon L15 Brush Truck",
    "2020 Falcon Advance 350",
    "2020 Falcon Advance 450 Ambulance",
    "2018 Falcon Global 450 Ambulance",
    "1956 Falcon Advance 600 Pumper",
    "Heavy Rescue",
    "Medical Bus",
    "Mobile Command Center",
    "Redline Fire Engine",
    "2014 Redline Heavy Tanker",
    "Redline Midmount Ladder",
    "Redline Rearmount Ladder",
    "2014 Redline Tanker",
    "2014 Redline Type 3 Brush Truck",
    "2020 Squad Falcon Advance+",
    "Special Operations Unit",
    # DOT
    "2010 Aikawa Street Sweeper",
    "1981 Chevlon L/35 Flatbed Tow Truck",
    "2015 Explorer Dump Truck",
    "2015 Explorer Flatbed Tow Truck",
    "2015 Explorer Salt Truck",
    "2015 Explorer Transport Truck",
    "2020 Falcon Advance 350",
    "2020 Falcon Advance 450 Bucket Truck",
    "2020 Falcon Advance 450 Roadside Assist",
    "2020 Falcon Advance 450 Tow Truck",
    "2020 Falcon Advance 450",
    "2018 Falcon Global 450 Utility",
    "Front Loader Tractor",
    "Forklift",
    "1995 Vellfire Evertt Crew Cab",
    "2013 Vinnimade Heavy Rotator",
    "2013 Vinnimade Heavy Wrecker",
]

# Unique vehicle models
VehicleModel = Literal[
    "4-Wheeler",
    "Aikawa Street Sweeper",
    "Arrow Phoenix Nationals",
    "Averon Anodic",
    "Averon Bremen VS Garde",
    "Averon LM",
    "Averon LM R",
    "Averon Q8",
    "Averon RS3",
    "Averon S5",
    "BKM Munich",
    "BKM Risen Roadster",
    "Bank Truck",
    "Brush Falcon Advance+",
    "Bullhorn BH15",
    "Bullhorn BH15 SSV",
    "Bullhorn Determinator",
    "Bullhorn Determinator C/T",
    "Bullhorn Determinator SFP Fury",
    "Bullhorn Determinator SFP Fury Blackjack Widebody",
    "Bullhorn Foreman",
    "Bullhorn Prancer",
    "Bullhorn Prancer C/T",
    "Bullhorn Prancer Colonel Fields",
    "Bullhorn Prancer Fury Widebody",
    "Bullhorn Prancer Fury Widebody Pursuit",
    "Bullhorn Prancer HotRod",
    "Bullhorn Prancer Pursuit",
    "Bullhorn Prancer S",
    "Bullhorn Prancer Talladega",
    "Bullhorn Pueblo Pursuit",
    "Bullhorn Pueblo SFP Fury",
    "Bullhorn Pueblo V6",
    "Canyon Descender",
    "Celestial Truckatron",
    "Celestial Type-7",
    "Celestial Type-6",
    "Celestial Type-5",
    "Chevlon Amigo LZR",
    "Chevlon Amigo S",
    "Chevlon Amigo ZL1",
    "Chevlon Antelope",
    "Chevlon Antelope SS",
    "Chevlon Camion",
    "Chevlon Camion GMT 800 LT",
    "Chevlon Camion GMT 800 LTS",
    "Chevlon Camion GMT 800 S",
    "Chevlon Camion PPV",
    "Chevlon Captain",
    "Chevlon Captain LTZ",
    "Chevlon Captain PPV",
    "Chevlon Commuter Van",
    "Chevlon Corbeta 1M Edition",
    "Chevlon Corbeta 8",
    "Chevlon Corbeta C2",
    "Chevlon Corbeta RZR",
    "Chevlon Corbeta X08",
    "Chevlon Inferno",
    "Chevlon L15 Brush Truck",
    "Chevlon L/15",
    "Chevlon L/15 Side Step",
    "Chevlon L/35 Extended",
    "Chevlon L/35 Flatbed Tow Truck",
    "Chevlon Landslide",
    "Chevlon Platoro",
    "Chevlon Platoro PPV",
    "Chevlon Revver",
    "Chryslus Champion",
    "Elysion Slick",
    "Emergency Services Falcon Advance+",
    "Explorer Dump Truck",
    "Explorer Flatbed Tow Truck",
    "Explorer Salt Truck",
    "Explorer Transport Truck",
    "Falcon Advance 100",
    "Falcon Advance 100 Holiday Edition",
    "Falcon Advance 350",
    "Falcon Advance 350 Royal Ranch",
    "Falcon Advance 450",
    "Falcon Advance 450 Ambulance",
    "Falcon Advance 450 Bucket Truck",
    "Falcon Advance 450 Roadside Assist",
    "Falcon Advance 450 Royal Ranch",
    "Falcon Advance 450 Tow Truck",
    "Falcon Advance XET",
    "Falcon Advance 600 Pumper",
    "Falcon Aquarius STP",
    "Falcon Coupe",
    "Falcon Coupe Hotrod",
    "Falcon eStallion",
    "Falcon Global 450 Ambulance",
    "Falcon Global 450 Utility",
    "Falcon Global 350",
    "Falcon Heritage",
    "Falcon Heritage Track",
    "Falcon Interceptor Sedan",
    "Falcon Interceptor Utility",
    "Falcon Prime Eques",
    "Falcon Prime Eques Interceptor",
    "Falcon Prime Eques Taxi",
    "Falcon Rampage Beast",
    "Falcon Rampage Bigfoot 2-Door",
    "Falcon Rampage Interceptor",
    "Falcon Rampage Prairie",
    "Falcon Scavenger",
    "Falcon Scavenger Royal Ranch",
    "Falcon Scavenger Security",
    "Falcon Scavenger Taxi",
    "Falcon Stallion 350",
    "Falcon Traveller PPV",
    "Falcon Traveller",
    "Farm Tractor 5100M",
    "Ferdinand Jalapeno Turbo",
    "Ferrari F8 Tributo",
    "Forklift",
    "Front-Loader Garbage Truck",
    "Front Loader Tractor",
    "Fuel Tanker",
    "Garbage Truck",
    "Heavy Rescue",
    "Kovac Heladera",
    "La Mesa Food Truck",
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
    "Mobile Command",
    "Mobile Command Center",
    "Navara Boundary",
    "Navara Horizon",
    "Navara Imperium",
    "News Van",
    "Overland Apache",
    "Overland Apache SFP",
    "Overland Buckaroo",
    "Pea Car",
    "Prisoner Transport Bus",
    "Redline Fire Engine",
    "Redline Heavy Tanker",
    "Redline Midmount Ladder",
    "Redline Rearmount Ladder",
    "Redline Tanker",
    "Redline Type 3 Brush Truck",
    "SWAT Armored Truck",
    "Sentinel Platinum",
    "Shuttle Bus",
    "Silhouette Carbon",
    "Special Operations Unit",
    "Squad Falcon Advance+",
    "Strugatti Ettore",
    "Stuttgart Executive",
    "Stuttgart Landschaft",
    "Stuttgart Runner Prisoner Transport",
    "Stuttgart Vierturig",
    "Sumo Reflexion",
    "Surrey 650S",
    "Takeo Experience",
    "Terrain Traveller",
    "Three Guys Food Truck",
    "Vellfire Everest VRD Max",
    "Vellfire Evertt Crew Cab",
    "Vellfire Evertt Extended Cab",
    "Vellfire Pioneer",
    "Vellfire Pioneer Targa",
    "Vellfire Prairie",
    "Vellfire Prima",
    "Vellfire Riptide",
    "Vellfire Runabout",
    "Vinnimade Heavy Rotator",
    "Vinnimade Heavy Wrecker",
]

_secondary_vehicles: List[VehicleName] = [
    "4-Wheeler",
    "Canyon Descender",
    "Forklift",
    "Lawn Mower",
]

_prestige_vehicles: List[VehicleModel] = [
    "Averon LM R",
    "Averon LM",
    "Averon Q8",
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

_fictional_textures = [
    "Standard",
    "Ghost",
    "SWAT",
    "Supervisor",
]

_default_textures = [
    *_fictional_textures,
    "Undercover",
]

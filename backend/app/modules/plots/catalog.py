SPECIES = (
    {
        "code": "GMELINA",
        "common_name": "Gmelina",
        "scientific_name": "Gmelina arborea",
    },
    {
        "code": "CASHEW",
        "common_name": "Cashew",
        "scientific_name": "Anacardium occidentale",
    },
    {
        "code": "NEEM",
        "common_name": "Neem",
        "scientific_name": "Azadirachta indica",
    },
    {
        "code": "MANGROVE",
        "common_name": "Mangrove",
        "scientific_name": "Rhizophora spp.",
    },
)

SPECIES_CODES = frozenset(item["code"] for item in SPECIES)

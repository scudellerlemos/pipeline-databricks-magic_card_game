import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from pyspark.sql.functions import col, current_timestamp, lit, month, to_timestamp, when, year
from pyspark.sql.types import BooleanType, FloatType, IntegerType, StringType, StructField, StructType


TABLE_TO_ENDPOINT = {
    "TB_BRONZE_CARDS": "cards",
    "TB_BRONZE_SETS": "sets",
    "TB_BRONZE_FORMATS": "formats",
    "TB_BRONZE_TYPES": "types",
    "TB_BRONZE_SUBTYPES": "subtypes",
    "TB_BRONZE_SUPERTYPES": "supertypes",
    "TB_BRONZE_CARDPRICES": "card_prices",
}


def create_bronze_api_config(secret_getter):
    return {
        "api_base_url": secret_getter("api_base_url", "https://api.magicthegathering.io/v1"),
        "scryfall_api_url": secret_getter("scryfall_api_url", "https://api.scryfall.com"),
        "batch_size": int(secret_getter("batch_size", "100")),
        "max_retries": int(secret_getter("max_retries", "3")),
        "years_back": int(secret_getter("years_back", "5")),
        "cards_max_pages": int(secret_getter("cards_max_pages", "100")),
        "price_workers": int(secret_getter("price_workers", "7")),
    }


def make_api_request(api_base_url, endpoint, params=None, retries=3, timeout=30):
    url = f"{api_base_url}/{endpoint}"
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code == 200:
                return response.json()
            if response.status_code == 429:
                time.sleep(min((attempt + 1) * 5, 60))
                continue
            if response.status_code == 503:
                time.sleep(min((attempt + 1) * 10, 120))
                continue
            if attempt < retries - 1:
                time.sleep(5)
                continue
            raise RuntimeError(f"Erro {response.status_code} na API {url}: {response.text[:500]}")
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(10)
                continue
            raise
        except requests.exceptions.RequestException:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise
    raise RuntimeError(f"Falha ao consumir API {url}")


def clean_cards_data(data):
    cleaned_data = []
    for item in data:
        cleaned_item = {}
        simple_fields = [
            "name", "manaCost", "type", "rarity", "set", "setName", "text",
            "artist", "number", "power", "toughness", "layout", "imageUrl",
            "originalText", "originalType", "id"
        ]
        for field in simple_fields:
            if field in item and item[field] is not None:
                try:
                    if field in ["cmc", "multiverseid"]:
                        cleaned_item[field] = float(item[field]) if field == "cmc" else int(item[field])
                    else:
                        cleaned_item[field] = str(item[field])
                except (ValueError, TypeError):
                    cleaned_item[field] = str(item[field]) if item[field] is not None else None
            else:
                cleaned_item[field] = None

        if "cmc" in item and item["cmc"] is not None:
            try:
                cleaned_item["cmc"] = float(item["cmc"])
            except (ValueError, TypeError):
                cleaned_item["cmc"] = None
        else:
            cleaned_item["cmc"] = None

        if "multiverseid" in item and item["multiverseid"] is not None:
            try:
                cleaned_item["multiverseid"] = int(item["multiverseid"])
            except (ValueError, TypeError):
                cleaned_item["multiverseid"] = None
        else:
            cleaned_item["multiverseid"] = None

        list_fields = ["colors", "colorIdentity", "types", "subtypes", "variations", "foreignNames", "printings", "legalities"]
        for field in list_fields:
            if field in item and item[field] is not None:
                cleaned_item[field] = json.dumps(item[field]) if isinstance(item[field], list) else str(item[field])
            else:
                cleaned_item[field] = None
        cleaned_data.append(cleaned_item)
    return cleaned_data


def cards_schema():
    return StructType([
        StructField("name", StringType(), True),
        StructField("manaCost", StringType(), True),
        StructField("cmc", FloatType(), True),
        StructField("colors", StringType(), True),
        StructField("colorIdentity", StringType(), True),
        StructField("type", StringType(), True),
        StructField("types", StringType(), True),
        StructField("subtypes", StringType(), True),
        StructField("rarity", StringType(), True),
        StructField("set", StringType(), True),
        StructField("setName", StringType(), True),
        StructField("text", StringType(), True),
        StructField("artist", StringType(), True),
        StructField("number", StringType(), True),
        StructField("power", StringType(), True),
        StructField("toughness", StringType(), True),
        StructField("layout", StringType(), True),
        StructField("multiverseid", IntegerType(), True),
        StructField("imageUrl", StringType(), True),
        StructField("variations", StringType(), True),
        StructField("foreignNames", StringType(), True),
        StructField("printings", StringType(), True),
        StructField("originalText", StringType(), True),
        StructField("originalType", StringType(), True),
        StructField("legalities", StringType(), True),
        StructField("id", StringType(), True),
    ])


def clean_sets_data(data):
    cleaned_data = []
    for item in data:
        if not isinstance(item, dict):
            continue
        cleaned_item = {}
        field_mappings = {
            "code": str,
            "name": str,
            "type": str,
            "border": str,
            "mkm_id": int,
            "mkm_name": str,
            "releaseDate": str,
            "gathererCode": str,
            "magicCardsInfoCode": str,
            "oldCode": str,
            "onlineOnly": bool,
            "source": str,
        }
        for field, field_type in field_mappings.items():
            if field in item:
                try:
                    cleaned_item[field] = field_type(item[field]) if item[field] is not None else None
                except (ValueError, TypeError):
                    cleaned_item[field] = str(item[field]) if item[field] is not None else None
            else:
                cleaned_item[field] = None

        booster_data = item.get("booster")
        if booster_data is not None:
            if isinstance(booster_data, list):
                for i, booster_item in enumerate(booster_data[:20]):
                    cleaned_item[f"booster_{i}"] = json.dumps(booster_item) if isinstance(booster_item, list) else str(booster_item)
                cleaned_item["booster"] = json.dumps(booster_data)
            else:
                cleaned_item["booster"] = str(booster_data)
        else:
            cleaned_item["booster"] = None
        for i in range(20):
            cleaned_item.setdefault(f"booster_{i}", None)
        cleaned_data.append(cleaned_item)
    return cleaned_data


def sets_schema():
    base = [
        StructField("code", StringType(), True),
        StructField("name", StringType(), True),
        StructField("type", StringType(), True),
        StructField("border", StringType(), True),
        StructField("mkm_id", IntegerType(), True),
        StructField("mkm_name", StringType(), True),
        StructField("releaseDate", StringType(), True),
        StructField("gathererCode", StringType(), True),
        StructField("magicCardsInfoCode", StringType(), True),
        StructField("booster", StringType(), True),
        StructField("oldCode", StringType(), True),
        StructField("onlineOnly", BooleanType(), True),
        StructField("source", StringType(), True),
    ]
    for i in range(20):
        base.append(StructField(f"booster_{i}", StringType(), True))
    return StructType(base)


def add_standard_metadata(df, endpoint, partition_mode="ingestion", release_col=None):
    df = df.withColumn("ingestion_timestamp", current_timestamp()) \
           .withColumn("source", lit("mtg_api")) \
           .withColumn("endpoint", lit(endpoint))

    if partition_mode == "release" and release_col and release_col in df.columns:
        return df.withColumn(
            "partition_year",
            when(col(release_col).isNotNull(), year(col(release_col))).otherwise(lit(datetime.now().year))
        ).withColumn(
            "partition_month",
            when(col(release_col).isNotNull(), month(col(release_col))).otherwise(lit(datetime.now().month))
        )

    return df.withColumn("partition_year", year(col("ingestion_timestamp"))) \
             .withColumn("partition_month", month(col("ingestion_timestamp")))


def extract_cards_from_api(spark, config):
    all_data = []
    page = 1
    while page <= config["cards_max_pages"]:
        data = make_api_request(
            config["api_base_url"],
            "cards",
            params={"page": page, "pageSize": config["batch_size"]},
            retries=config["max_retries"],
        )
        page_data = data.get("cards", []) if data else []
        if not page_data:
            break
        all_data.extend(clean_cards_data(page_data))
        page += 1
        time.sleep(0.5)
    if not all_data:
        raise ValueError("Nenhum dado retornado pela API de cards")
    df = spark.createDataFrame(all_data, cards_schema())
    return add_standard_metadata(df, "cards")


def extract_sets_from_api(spark, config):
    data = make_api_request(config["api_base_url"], "sets", retries=config["max_retries"])
    sets_data = data.get("sets", []) if data else []
    if not sets_data:
        raise ValueError("Nenhum dado retornado pela API de sets")
    df = spark.createDataFrame(clean_sets_data(sets_data), sets_schema())
    return add_standard_metadata(df, "sets", partition_mode="release", release_col="releaseDate")


def extract_reference_from_api(spark, config, endpoint, field_name):
    data = make_api_request(config["api_base_url"], endpoint, retries=config["max_retries"])
    values = data.get(endpoint, []) if data else []
    cleaned = [{field_name: item} for item in values if isinstance(item, str)]
    if not cleaned:
        raise ValueError(f"Nenhum dado retornado pela API de {endpoint}")
    df = spark.createDataFrame(cleaned)
    return add_standard_metadata(df, endpoint)


def get_card_price(config, card_name):
    url = f"{config['scryfall_api_url']}/cards/named?exact={card_name}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "name": data.get("name"),
                "set": data.get("set"),
                "rarity": data.get("rarity"),
                "usd": data.get("prices", {}).get("usd"),
                "eur": data.get("prices", {}).get("eur"),
                "tix": data.get("prices", {}).get("tix"),
                "scryfall_uri": data.get("scryfall_uri"),
                "image_url": data.get("image_uris", {}).get("normal") if data.get("image_uris") else None,
                "ingestion_timestamp": datetime.utcnow().isoformat(),
                "source": "scryfall",
            }
        return {"name": card_name, "error": f"Status {resp.status_code}"}
    except Exception as e:
        return {"name": card_name, "error": str(e)}


def fetch_card_names_from_api(config):
    all_names = []
    page = 1
    while page <= config["cards_max_pages"]:
        data = make_api_request(
            config["api_base_url"],
            "cards",
            params={"page": page, "pageSize": config["batch_size"]},
            retries=config["max_retries"],
        )
        page_data = data.get("cards", []) if data else []
        if not page_data:
            break
        all_names.extend([item.get("name") for item in page_data if item.get("name")])
        page += 1
        time.sleep(0.5)
    distinct_names = list(dict.fromkeys(all_names))
    if not distinct_names:
        raise ValueError("Nenhum nome de card retornado pela API")
    return distinct_names


def extract_card_prices_from_api(spark, config):
    card_names = fetch_card_names_from_api(config)
    prices = []
    batch_size = config["batch_size"]
    total_cards = len(card_names)
    num_batches = (total_cards + batch_size - 1) // batch_size

    for batch_idx in range(num_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, total_cards)
        batch_names = card_names[start:end]
        with ThreadPoolExecutor(max_workers=config["price_workers"]) as executor:
            future_to_name = {executor.submit(get_card_price, config, name): name for name in batch_names}
            batch_prices = []
            for future in as_completed(future_to_name):
                batch_prices.append(future.result())
        batch_prices_sorted = [next(bp for bp in batch_prices if bp.get("name") == name) for name in batch_names if any(bp.get("name") == name for bp in batch_prices)]
        prices.extend(batch_prices_sorted)

    if not prices:
        raise ValueError("Nenhum preço retornado pela API de card_prices")

    df = spark.createDataFrame(prices)
    df = df.withColumn("endpoint", lit("card_prices"))
    return df.withColumn("partition_year", year(to_timestamp("ingestion_timestamp"))) \
             .withColumn("partition_month", month(to_timestamp("ingestion_timestamp")))


def extract_from_api(spark, table_name, config):
    if table_name == "TB_BRONZE_CARDS":
        return extract_cards_from_api(spark, config)
    if table_name == "TB_BRONZE_SETS":
        return extract_sets_from_api(spark, config)
    if table_name == "TB_BRONZE_FORMATS":
        return extract_reference_from_api(spark, config, "formats", "format_name")
    if table_name == "TB_BRONZE_TYPES":
        return extract_reference_from_api(spark, config, "types", "type_name")
    if table_name == "TB_BRONZE_SUBTYPES":
        return extract_reference_from_api(spark, config, "subtypes", "subtype_name")
    if table_name == "TB_BRONZE_SUPERTYPES":
        return extract_reference_from_api(spark, config, "supertypes", "supertype_name")
    if table_name == "TB_BRONZE_CARDPRICES":
        return extract_card_prices_from_api(spark, config)
    raise ValueError(f"Tabela Bronze sem extractor de API: {table_name}")

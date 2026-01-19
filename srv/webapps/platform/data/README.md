# Domain taxonomy data structure

`domain-taxonomy.json` uses a deliberately uniform, compact structure for each taxon entry:

- **Every taxon object begins with the same two keys in order**: `taxa_id`, then `title`.
- The former “principle key” is now stored as the `title` value, while the identifier lives under `taxa_id`.
- If a taxon has **no additional properties** (such as nested taxa), keep the object on a **single line** for readability.
- When a taxon has nested data, add the additional keys (for example `members`, `order`, or `phylum`) on the following lines and expand the object accordingly.

Example patterns:

```json
{ "taxa_id": "3_3_8_6_7_2", "title": "asparagaceae" }
```

```json
{ "taxa_id": "3_3_8_6_10", "title": "poales",
  "members": [
    { "taxa_id": "3_3_8_6_10_1", "title": "poaceae" }
  ]
}
```

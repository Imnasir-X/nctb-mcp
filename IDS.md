# NCTB shared ID scheme (dataset `nctb-data` v0.1.0-draft)

Owner of this file: the nctb-mcp agent (shared data layer). The banglaedu-bench agent reuses these IDs.
Status: **draft**. Chapter IDs below are final for the 2026 edition. Topic (section) IDs are filled in
as the per-page extraction completes. Every record in the data carries `verified: false` until a human checks it.

## Grammar

```
nctb:<subject>:<class>:<version>:ch<NN>                 chapter
nctb:<subject>:<class>:<version>:ch<NN>:t<NN>           topic  = numbered section "N.M" printed in the book
nctb:<subject>:<class>:<version>:ch<NN>:t<NN>:s<NN>     subtopic = "N.M.K" (only where the book prints one)
nctb:<subject>:<class>:<version>:ch<NN>:o<NN>           learning objective (chapter-opening list, in printed order)
nctb:<subject>:<class>:<version>:ch<NN>:we<NN>          worked example (গাণিতিক উদাহরণ / Mathematical example), in printed order
nctb:<subject>:<class>:<version>:ch<NN>:ex:<kind><NN>   end-of-chapter exercise item, in printed order within its kind
```

| Segment         | Values                                                                                                                 | Notes                                                                                                                                      |
| --------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| subject         | `phy`                                                                                                                  | Physics. Later: `chem`, `bio`, `hmath`, `math`, `ict`.                                                                                     |
| class           | `c9-10`                                                                                                                | The SSC Physics book is one book for Classes 9 and 10 combined, so the class segment is `c9-10`, never `c9`. Later: `c1` … `c8`, `c11-12`. |
| version         | `bn`, `en`                                                                                                             | NCTB "Bangla version" and "English version" books. Separate books with separate page numbers.                                              |
| NN              | two digits, zero-padded                                                                                                | `ch03`, `t02`. Topic numbers equal the book's own section numbers (section ৩.২ → `t02`).                                                   |
| kind (exercise) | `mcq`, `sq` (short / অতি সংক্ষিপ্ত + সংক্ষিপ্ত), `cq` (সৃজনশীল / creative), `num` (গাণিতিক সমস্যা / numerical problem) | Assigned from the headings printed in the অনুশীলনী / Exercise section.                                                                     |

Regex: `^nctb:[a-z]+:c\d{1,2}(-\d{1,2})?:(bn|en):ch\d{2}(:(t\d{2}(:s\d{2})?|o\d{2}|we\d{2}|ex:(mcq|sq|cq|num)\d{2}))?$`

### Language-neutral concept key

`concept_key` = the ID with the version segment removed, e.g. `nctb:phy:c9-10:ch03:t02`.
Use it to link the Bangla and English books **only where `bn` and `en` section numbering is checked to match**
(each record states `concept_key_checked: true|false`). The bench should store the full versioned topic ID
of the book a question was written from, and may also store the concept key.

### Stability rules

1. IDs are scoped to the **2026 edition** (`edition: 2026` on every record; dataset tag `nctb-data@0.1.0`).
2. An ID is never reused for a different section. If a later edition renumbers sections, the new edition gets a
   mapping file (`mappings/2026-to-2027.json`); old IDs stay valid for the 2026 edition.
3. Typo fixes in titles do not change IDs. Only structure changes do.

## Physics, Class 9-10, 2026 edition: chapters

Verified by eye against the printed contents page (সূচিপত্র, PDF page 5 of the Bangla book; CONTENTS, PDF page 5 of the English book)
on 2026-11-07 by the agent. `verified` in the data stays `false` until a human checks.

| Chapter ID (bn)        | Bangla title                | Printed p. (bn) | English title (en book)                    | Printed p. (en) |
| ---------------------- | --------------------------- | --------------- | ------------------------------------------ | --------------- |
| nctb:phy:c9-10:bn:ch01 | ভৌত রাশি এবং তাদের পরিমাপ   | ১               | Physical Quantities and Their Measurements | 1               |
| nctb:phy:c9-10:bn:ch02 | গতি                         | ৩২              | Motion                                     | 31              |
| nctb:phy:c9-10:bn:ch03 | বল                          | ৬২              | Force                                      | 61              |
| nctb:phy:c9-10:bn:ch04 | কাজ, ক্ষমতা ও শক্তি         | ৯৮              | Work, Power and Energy                     | 98              |
| nctb:phy:c9-10:bn:ch05 | পদার্থের অবস্থা ও চাপ       | ১২৭             | State of Matter and Pressure               | 127             |
| nctb:phy:c9-10:bn:ch06 | বস্তুর ওপর তাপের প্রভাব     | ১৫৯             | Effect of Heat on Matter                   | 160             |
| nctb:phy:c9-10:bn:ch07 | তরঙ্গ ও শব্দ                | ১৮৬             | Waves and Sound                            | 187             |
| nctb:phy:c9-10:bn:ch08 | আলোর প্রতিফলন               | ২১০             | Reflection of Light                        | 211             |
| nctb:phy:c9-10:bn:ch09 | আলোর প্রতিসরণ               | ২৪১             | Refraction of light                        | 242             |
| nctb:phy:c9-10:bn:ch10 | স্থির বিদ্যুৎ               | ২৭০             | Static Electricity                         | 270             |
| nctb:phy:c9-10:bn:ch11 | চল বিদ্যুৎ                  | ২৯৮             | Current Electricity                        | 299             |
| nctb:phy:c9-10:bn:ch12 | বিদ্যুতের চৌম্বক ক্রিয়া    | ৩২৯             | Magnetic Effects of Current                | 330             |
| nctb:phy:c9-10:bn:ch13 | তেজস্ক্রিয়তা ও ইলেকট্রনিকস | ৩৪৬             | Radioactivity and Electronics              | 347             |

English chapter IDs are the same with `:en:` (e.g. `nctb:phy:c9-10:en:ch03`). Thirteen chapters in the 2026 edition
(the 2017-era book had a different chapter list; do not reuse older chapter lists).

## Topics

The full topic list (every numbered section, both versions, with printed and PDF page) is the `topics` array of
`data/physics-9-10-bn.json` and `data/physics-9-10-en.json` (the pipeline also writes a readable `topics.md` next to
the shared data). Treat the data files as the authoritative list; this file only documents the scheme.

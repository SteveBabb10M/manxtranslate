# Yn Caaghstan Screeuee

## The Manx Writing Standard

**A guide to grammar, usage, and style for written Manx Gaelic**

*Working draft — grows with practice*

---

## Preface

This document serves two purposes that Irish separates into two publications: the prescriptive grammar standard (*An Caighdeán Oifigiúil*) and the plain-language writing guide (*Treoir maidir le Gaeilge Shoiléir a Scríobh*). For Manx, with its smaller writing community and single historical orthographic tradition, a unified document makes more sense.

The standard is designed to be:

- **Authoritative but living** — rules are numbered and citable, but the document grows as new decisions are made during translation and composition work.
- **Practically grounded** — every rule includes examples drawn from actual usage: the Manx Bible, the Book of Common Prayer, traditional literature, and modern translation work including *The Revestment*.
- **Machine-readable** — the numbered rule structure maps directly onto the `grammar_rules` table in the translation toolkit database, so rules can be queried programmatically during translation sessions.

### Scope

Unlike the Irish CO, which had to arbitrate between three living dialect traditions, the Manx standard works from a single orthographic base: the traditional spelling established in the Bible translation (1610–1772) and used consistently through the classical period. Where the historical corpus is thin or silent — modern vocabulary, technical terminology, constructions not attested in the literature — the standard makes explicit rulings, drawing on cognate forms in Irish and Scottish Gaelic adapted to Manx orthography and phonology.

### How to Use This Document

**For translators**: Look up specific rules by number when making decisions. Each rule is tagged with a category (e.g., `MUTATION`, `VERB`, `ARTICLE`) that matches the database query categories in the translation toolkit.

**For writers**: The style guidance in Part III applies to all original Manx composition, not just translation work.

**For the toolkit**: Rules are ingested into the `grammar_rules` table by the `build_db.py` script. The format is: rule number, category tag, rule text, examples.

---

## Contents

### Part I — Grammar Rules (*Reillyn Ghrammeydys*)

1. [The Article (*Yn Art*)](#1-the-article)
2. [The Noun (*Yn Ennym*)](#2-the-noun)
3. [The Adjective (*Yn Aght-ockle*)](#3-the-adjective)
4. [The Verb (*Yn Breear*)](#4-the-verb)
5. [The Copula (*She*)](#5-the-copula)
6. [The Pronoun (*Yn Far-ennym*)](#6-the-pronoun)
7. [Prepositions (*Roish-ocklyn*)](#7-prepositions)
8. [The Numeral (*Yn Earroo*)](#8-the-numeral)
9. [The Adverb (*Yn Ard-ockle*)](#9-the-adverb)
10. [Initial Mutations (*Caghlaaghyn-toshee*)](#10-initial-mutations)
11. [The Relative Clause (*Yn Cloose Dooghyssagh*)](#11-the-relative-clause)
12. [Word Order and Sentence Structure (*Oardagh-focklyn*)](#12-word-order)

### Part II — Orthography and Spelling (*Lettyrys as Spellyn*)

13. [The Manx Alphabet and Sound Values](#13-the-alphabet)
14. [Spelling Conventions](#14-spelling-conventions)
15. [Hyphenation](#15-hyphenation)
16. [Capitalisation](#16-capitalisation)
17. [Punctuation](#17-punctuation)
18. [Loanwords and Neologisms](#18-loanwords)
19. [Place Names and Personal Names](#19-names)

### Part III — Style and Usage (*Aght as Ymmyd*)

20. [General Principles of Clear Manx](#20-clear-manx)
21. [Sentence Construction](#21-sentence-construction)
22. [Addressing the Reader](#22-addressing-reader)
23. [Terminology and Consistency](#23-terminology)
24. [Translation-Specific Guidance](#24-translation-guidance)
25. [Register and Tone](#25-register)

### Appendices

- [A. Summary Mutation Tables](#appendix-a)
- [B. Verb Paradigm Tables](#appendix-b)
- [C. Noun Declension Patterns](#appendix-c)
- [D. Numeral Tables](#appendix-d)
- [E. Decisions Log — *The Revestment*](#appendix-e)

---

# Part I — Grammar Rules

---

## 1. The Article

**Category tag: `ARTICLE`**

### 1.1 General

1.1.1 Manx has one article — the definite article. There is no indefinite article. The absence of *yn* / *ny* before a noun indicates indefiniteness.

> *yn thie* — the house
> *thie* — a house

1.1.2 The article has two forms: **yn** (singular) and **ny** (plural; also used with singular in the genitive).

> *yn dooinney* — the man
> *ny deiney* — the men
> *kione ny bleeaney* — the end of the year

1.1.3 The article is not capitalised in the middle of a sentence, except in titles and proper names written in isolation (e.g., on headings, signs, or official documents).

> *Va'n Chiarn loayrt rish Moses.* — The Lord spoke to Moses.
> But as a heading: *Yn Chiarn* — The Lord

### 1.2 The Article with Initial Mutations

1.2.1 The singular article **yn** triggers the following changes to the initial consonant of the noun:

(a) Before feminine singular nouns, **yn** causes lenition (see §10 for full mutation tables):

> *yn vean* (the woman; radical: *ben*)
> *yn chlagh* (the stone; radical: *clagh*)
> *yn çhiarn* (the lord; radical: *chiarn*)

(b) Before masculine nouns beginning with a vowel, **t-** is prefixed:

> *yn t-ushtey* — the water

(c) Before feminine nouns beginning with **s** + vowel/l/n/r, the **s** is replaced by **t**:

> *yn toshiaght* (the beginning; radical: *soshiaght*) [CHECK — verify specific examples from corpus]

1.2.2 The plural article **ny** triggers eclipsis (nasalisation):

> *ny deiney* — the men
> *ny kirree* — the sheep [CHECK — verify eclipsis effect or lack thereof on k-]

1.2.3 In the genitive, **ny** is used with both singular and plural nouns, and triggers eclipsis:

> *dorrys ny h-ollee* — the door of the cattle

### 1.3 The Article with Prepositions

1.3.1 Several common prepositions combine with the article **yn** to form contracted (fused) forms:

> *ayns yn* → *'syn / sy* (in the)
> *ec yn* → *ec y* (at the)
> *er yn* → *er y* (on the)
> *fo yn* → *fo yn* (under the)
> *gys yn* → *gys y* (to the)
> *lesh yn* → *lesh y* (with the)
> *rish yn* → *rish y* (against the)
> *veih yn* → *veih'n* (from the)

**Note**: These contracted forms are standard in all registers. The full uncontracted forms (*ayns yn*, etc.) are acceptable but less natural.

### 1.4 Use of the Article

1.4.1 The article is used in Manx in several contexts where English omits it:

(a) Titles and offices:

> *Yn Chiarn Dooinney* — the Lord [as title]
> *yn Ree* — the King

(b) Days of the week:

> *Yn Lhein* — Monday
> *Yn Vayrt* — Tuesday

(c) Festivals and seasons:

> *yn Nollick* — Christmas
> *yn Chaisht* — Easter
> *yn geurey* — winter

(d) Abstract concepts used generically:

> *Ta graih mie.* — Love is good.

But when the concept is specified or particularised, the article appears:

> *Yn graih ta ainmit ayns y lioar shoh...* — The love mentioned in this book...

1.4.2 The article is **not** used before possessive adjectives:

> *my hie* — my house (NOT *yn my hie*)

---

## 2. The Noun

**Category tag: `NOUN`**

### 2.1 General

2.1.1 Manx nouns have two genders: masculine and feminine. Gender is largely unpredictable and must be learned with each noun, though some patterns exist (see §2.1.3).

2.1.2 Manx nouns inflect for number (singular/plural) and, in certain environments, show genitive forms. The old dative case, still visible in fixed phrases, is not productively used.

2.1.3 Gender tendencies (not absolute rules):

(a) Typically masculine:
- Nouns ending in a broad consonant: *fer* (man), *thie* (house)
- Verbal nouns: *geddyn* (getting), *goll* (going)
- Trees and some plants: *billey* (tree)

(b) Typically feminine:
- Nouns ending in *-ag*: *caillag* (girl), *skeealag* (story)
- Countries and territories: *Sostyn* (England), *Nerin* (Ireland)
- Rivers: *yn Awin* (the river)
- Abstract nouns ending in *-ys*: *seyrsnys* (freedom), *ooashley* (honour) [CHECK — verify gender of *-ys* nouns; some may be masculine]

### 2.2 Plural Formation

2.2.1 Manx forms plurals through several patterns. The most common:

(a) **-yn** suffix (the most productive and default for new words):

> *lioar* → *lioaryn* (books)
> *blein* → *bleeantyn* (years)

(b) **-aghyn** suffix:

> *skeeal* → *skeealyn / skeeallaghyn* (stories) [CHECK — confirm both forms]

(c) **-ee** suffix (common with agent nouns):

> *sidoor* → *sidooryn* (soldiers) — verified in `pairs-gv.txt`

(d) **Internal vowel change** (strong plurals):

> *fer* → *fir* (men)
> *ben* → *mraane* (women)
> *dooinney* → *deiney* (men/people)

(e) **Irregular plurals** must be learned individually. Common examples:

> *ollagh* (cattle — collective noun; from Irish *eallach*)
> *eayn* → *eayin* (lambs) — verified: *eayin* maps to Irish *uain*

2.2.2 When both a regular (-yn) and an older/irregular plural exist, prefer the form attested in the classical literature. Where the classical literature offers no clear precedent, the **-yn** form is acceptable.

### 2.3 The Genitive

2.3.1 The genitive is formed by placing the possessed noun before the possessor, without a linking particle:

> *dorrys y thie* — the door of the house (lit: door the house)
> *ree ny Manninee* — king of the Manx people

2.3.2 In the genitive construction, the second noun (the possessor) is lenited if it follows the singular article and is a noun that undergoes lenition in this position:

> *bun ny croink* — the foot of the hill (*cronk* → *croink* in genitive — verified: maps to Irish *cnoic*)

2.3.3 When the genitive noun is feminine singular, the article used is **ny** (same form as the plural article):

> *kione ny bleeaney* — the end of the year (*blein*, fem.)

### 2.4 Nouns in Fixed Phrases

2.4.1 Many common expressions preserve older case forms. These should be learned as fixed phrases, not analysed as productive grammar:

> *ec y thie* — at home
> *er y thalloo* — on the ground
> *ayns y voghrey* — in the morning

---

## 3. The Adjective

**Category tag: `ADJECTIVE`**

### 3.1 General

3.1.1 Adjectives in Manx normally follow the noun they modify:

> *dooinney mooar* — a big man
> *ben vie* — a good woman

3.1.2 A small set of adjectives may precede the noun. These are often lenited when they do so:

> *shenn dooinney* — an old man (*shenn* < *çhenn*)
> *drogh earish* — bad weather

### 3.2 Agreement

3.2.1 Adjectives show gender agreement with feminine singular nouns by undergoing lenition:

> *ben vooar* — a big woman (masc: *dooinney mooar*)
> *clagh vane* — a white stone (masc: *thie bane*)

3.2.2 In the plural, adjectives are generally **not** lenited, regardless of gender:

> *mraane mooarey* — big women
> *deiney mooarey* — big men

3.2.3 Some adjectives have distinct plural forms (ending in **-ey**):

> *mooar* → *mooarey* (big, pl.)
> *beg* → *beggey* (small, pl.)
> *bane* → *baney* (white, pl.) — the adjective form *bane* maps to Irish *bán/báin/báine*; plural *baney* follows the standard *-ey* pattern

### 3.3 Comparison

3.3.1 The comparative is formed with **ny s'** (or **ny smoo** for longer adjectives) and the comparative form of the adjective:

> *Ta Juan ny s'troshey na Peddyr.* — John is stronger than Peter.

3.3.2 The superlative uses **yn** / **s'** and the same comparative form:

> *She Juan y fer s'troshey.* — John is the strongest man.

3.3.3 Common irregular comparatives:

> *mie* (good) → *share* (better/best)
> *olk* (bad) → *smessey* (worse/worst)
> *mooar* (big) → *moo* (bigger/biggest)
> *beg* (small) → *loo* / *sloo* (smaller/smallest)

---

## 4. The Verb

**Category tag: `VERB`**

### 4.1 General

4.1.1 Manx is a VSO (Verb-Subject-Object) language. The verb comes first in the clause:

> *Lhaih yn dooinney yn lioar.* — The man read the book.

4.1.2 Manx verbs have two main conjugation types, distinguished by the past tense formation:

(a) **First conjugation** — past tense formed by lenition of the initial consonant (with or without suffix):

> *cur* → *hug* (gave; irregular but illustrative of pattern)
> *fakin* → *honnick* (saw; irregular)

(b) **Second conjugation** — past tense formed with the suffix **-ee** (added to the verbal stem):

> *toshiaght* → *hoshee* [CHECK — clarify stem vs verbal noun forms]

**Note**: The boundary between "conjugations" in Manx is less clear-cut than in Irish. Many verbs are best learned individually.

### 4.2 Tenses and Moods

4.2.1 Manx has the following tense/mood forms:

| Tense/Mood | Positive | Negative | Interrogative |
|---|---|---|---|
| Present | *ta* | *cha nel* | *vel...?* |
| Past | *va* | *cha row* | *row...?* |
| Future | *bee* | *cha bee* | *bee...?* |
| Conditional | *veagh* | *cha beagh* | *beagh...?* |
| Imperative | (bare stem) | *ny* + verbal noun | — |

**Note**: This table shows the forms of *ve* (to be), the most common verb. Other verbs form tenses differently — see individual verb entries and §4.3–4.5.

### 4.3 The Present Tense

4.3.1 The present tense is normally formed with **ta** + subject + **ag** + verbal noun:

> *Ta mee ag screeu.* — I am writing.
> *Ta'n dooinney ag lhaih lioar.* — The man is reading a book.

4.3.2 For habitual actions, the same construction is used, often with an adverb of frequency:

> *Ta mee ag goll dagh laa.* — I go every day.

### 4.4 The Past Tense

4.4.1 Regular past tense is formed by leniting the initial consonant of the verb:

> *cur* → *hur mee* (I put/gave) [CHECK exact forms]
> *faagail* → *daag mee* (I left)

4.4.2 The negative past uses **cha** + dependent form of the verb:

> *Cha daag mee.* — I did not leave.

4.4.3 The interrogative past uses the dependent form with eclipsis (where applicable):

> *Daag oo?* — Did you leave? [CHECK — confirm question formation pattern]

### 4.5 The Future Tense

4.5.1 The future is formed with the future stem + personal endings, or more commonly in spoken/modern Manx with auxiliary constructions:

> *Nee'm screeu.* — I will write.
> *Bee mee screeu.* — I will be writing.

4.5.2 The negative future: **cha jean** + subject + verbal noun:

> *Cha jean mee screeu.* — I will not write.

### 4.6 The Verbal Noun

4.6.1 The verbal noun is the citation form of Manx verbs and is used in most periphrastic constructions. It functions both as a verb form (after auxiliaries) and as a noun (as the object of prepositions).

> *ag screeu* — writing (after auxiliary)
> *lurg screeu yn lettyr* — after writing the letter (after preposition)

4.6.2 Common verbal noun endings include: *-ey*, *-aghey*, *-al*, *-eil*, *-yn*, and bare stems.

### 4.7 Irregular Verbs

4.7.1 The most important irregular verbs (all forms verified from UD_Manx-Cadhan corpus; lemma in parentheses):

(a) **goll/gow** (lemma: *gow*) — to go: past *hie* (lenited), dependent past *jagh*, future *hem/hed*, imperative *gow/gow-jee*
(b) **çheet/tar** (lemma: *tar*) — to come: past *haink* (lenited), dependent past *daink* (eclipsed), future *hig/jig*, conditional *darragh*, imperative *tar*
(c) **jannoo/jean** (lemma: *jean*) — to do/make: past *ren*, future *nee/nee'm*, conditional *yinnagh* (lenited) / *jinnagh*, imperative *jean*
(d) **geddyn/fow** (lemma: *fow*) — to get/find: past *hooar* (lenited), dependent past *dooar* (eclipsed), future *yiow* (lenited) / *vow* (eclipsed), imperative *fow*
(e) **fakin/faik** (lemma: *faik*) — to see: past *honnick* (lenited), dependent past *vaik/naik* (eclipsed), dependent future *vaikmayd*
(f) **gra/abbyr** (lemma: *abbyr*) — to say: past *dooyrt*, future *jir*, conditional *niarragh*, imperative *abbyr*
(g) **cur** (lemma: *cur*) — to give/put: past *hug* (lenited), dependent past *dug* (eclipsed), future *ver* (eclipsed), *verym/ver-ym* (1sg), imperative *cur*
(h) **goaill/gow** — to take: past *ghow* (lenited), future *gowym*, imperative *gow*
(i) **clashtyn** — to hear: verbal noun *clashtyn*, lenited *chlashtyn* (attested in UD corpus)
(j) **ve/bee** (lemma: *bee*) — to be: present *ta/t'*, interrogative *vel*, negative *nel*, past *va/v'*, dependent past *row*, future *bee*, conditional *beagh*, future habitual *vees* (lenited)

**Note**: Full paradigms for each irregular verb will be given in Appendix B.

### 4.8 The Autonomous/Impersonal Form

4.8.1 Manx, like Irish and Scottish Gaelic, has an autonomous (impersonal) verb form — the equivalent of the Irish *saorbhriathar*. This is used when the agent is unknown, unimportant, or deliberately left unstated:

> *Hie skeeal magh...* — Word went out... [CHECK — find attested autonomous examples]
> *Va'n leigh currit magh.* — The law was promulgated. (lit: was the law put out)

4.8.2 In modern Manx writing, the passive sense is often expressed with *ve* + past participle, following the same pattern as the periphrastic constructions:

> *Va eh er ny yannoo.* — It was done. (lit: was it after its doing)

---

## 5. The Copula

**Category tag: `COPULA`**

### 5.1 General

5.1.1 Manx has a copula **she** (present) / **by** (past/conditional), distinct from the substantive verb **ta** (is/are). The copula is used for identification and classification; the substantive verb for description, location, and states.

> *She dooinney mie eh.* — He is a good man. (copula: classification)
> *Ta'n dooinney mie.* — The man is good. (substantive: description)

5.1.2 The copula is used:

(a) To identify: *She Juan eh.* — It is John. / He is John.
(b) To classify: *She fer-ynsee eh.* — He is a teacher.
(c) For emphasis (clefting): *She Juan ren eh.* — It was John who did it.

### 5.2 Forms of the Copula

5.2.1 Present: **she** (affirmative), **cha nee** (negative), **nee...?** (interrogative)
5.2.2 Past/conditional: **by** / **b'** (affirmative), **cha by** (negative), **by...?** (interrogative)

Attested copular sentences from the UD_Manx-Cadhan corpus:

> *She dooinney-ooasle va'n ayr echey.* — His father was a gentleman.
> *She bunstoo lorgagh eh yiarn son dagh ooilley organe bioag, faggys.* — Iron is an essential trace element for almost every organism.
> *She boandyrey mish ayns Glaschu.* — I am a farmer in Glasgow.
> *She Sostynagh veih'n chlean eh.* — He is an Englishman from the in-laws.
> *She mooaralagh eh.* — He is proud/arrogant.
> *She yn Vritaan y lieh-innys smoo 'sy Rank.* — Britain is the biggest island in the Kingdom.
> *She Manninagh mish ta Gaelg aym.* — I am a Manx person who has Manx.

### 5.3 Style Guidance: Using the Copula

5.3.1 Use the copula for variety and emphasis in prose. A text that uses only the substantive verb *ta* throughout becomes monotonous. Mix copular and verbal sentences for natural rhythm — this is directly parallel to the advice in the Irish plain language guide.

> Flat: *Ta Juan ny er-ynsee. Ta eh cummal ayns Doolish.*
> Better: *She fer-ynsee eh Juan. Ta eh cummal ayns Doolish.*

---

## 6. The Pronoun

**Category tag: `PRONOUN`**

### 6.1 Personal Pronouns

6.1.1 The personal pronouns are:

| Person | Singular | Plural |
|---|---|---|
| 1st | *mee* (I/me) | *shin* (we/us) |
| 2nd | *oo* (you, sg.) | *shiu* (you, pl.) |
| 3rd masc. | *eh* (he/him) | *ad* (they/them) |
| 3rd fem. | *ee* (she/her) | *ad* (they/them) |

### 6.2 Possessive Adjectives

6.2.1 Possessive adjectives precede the noun and trigger mutations (verified from UD_Manx-Cadhan corpus):

| Person | Form | Mutation | Example (attested) |
|---|---|---|---|
| 1st sg. | *my* | lenition | *my hie* (my house), *my chione* (my head), *my hooill* (my eye), *my ghraih* (my love), *my eeackle* (my tooth; *f* dropped) |
| 2nd sg. | *dty* | lenition | *dty hie* (your house) |
| 3rd sg. masc. | *e* | lenition | *e chione* (his head), *e chooid* (his stuff), *e hamyr* (his room), *e vair* (his finger), *e voir* (his mother) |
| 3rd sg. fem. | *e* | **no lenition**; *h-* before vowels | *e kione* (her head), *e cloan* (her children), *e mac* (her son), *e h-ayr* (her father), *e hinneenyn* (her daughters), *e hoohyn* (her eggs) |
| 1st pl. | *nyn* | eclipsis | *nyn dhie* (our house), *nyn mast* (among us), *nyn goyrt* (our giving) |
| 2nd pl. | *nyn* | eclipsis | *nyn dhie* (your house) |
| 3rd pl. | *nyn* | eclipsis | *nyn dhie* (their house) |

**Key distinction**: 3rd sg. masculine *e* causes lenition; 3rd sg. feminine *e* does **not** lenite consonants but prefixes *h-* before vowels. This is confirmed by the UD corpus: *e chione* (his head, Form=Len) vs *e kione* (her head, no mutation marker).

**Note**: *nyn* is the same form for 1st, 2nd, and 3rd plural. Context disambiguates.

### 6.3 Prepositional Pronouns

6.3.1 Prepositions combine with pronouns to form synthetic (fused) forms. The main prepositional pronouns (verified from Scannell's `pairs-gv.txt`):

| | *ec* (at) | *er* (on) | *da* (to/for) | *lesh* (with) | *rish* (to/against) | *veih* (from) |
|---|---|---|---|---|---|---|
| 1sg | *aym* | *orrym* | *dou* | *lhiam* | *rhym* | *voym* |
| 2sg | *ayd* | *ort* | *dhyt* | *lhiat* | *rhyt* | *void* |
| 3sg m | *echey* | *er* | *da* | *lesh* | *rish* | *voish* |
| 3sg f | *eck* | *urree* | *jee* | *lhee* | *r'ee* | *voee* |
| 1pl | *ain* | *orrin* | *dooin* | *lhien* | *rooin* | *voin* |
| 2pl | *eu* | *erriu* | *diu* | *lhiu* | *riu* | *voiu* |
| 3pl | *oc* | *orroo* | *daue* | *lhieu* | *roo* | *voo* |

---

## 7. Prepositions

**Category tag: `PREPOSITION`**

### 7.1 Simple Prepositions

7.1.1 The most common simple prepositions:

> *ec* — at
> *er* — on
> *ayns* — in
> *da* / *dy* — to, for
> *lesh* — with
> *veih* — from
> *rish* — to, against, during
> *fo* — under
> *harrish* — over, across
> *trooid* — through
> *mygeayrt* — about, around
> *eddyr* — between
> *gys* — to, towards

### 7.2 Compound Prepositions

7.2.1 Compound prepositions are formed from simple preposition + noun (+ simple preposition). The governed noun follows in the genitive where applicable:

> *er son* — for (on account of)
> *er coontey* — because of
> *mychione* — concerning
> *lurg* — after
> *roish* — before
> *mastey* — among

---

## 8. The Numeral

**Category tag: `NUMERAL`**

### 8.1 General

8.1.1 Manx preserves a vigesimal (base-20) counting system alongside a decimal one. The traditional vigesimal system should be preferred in literary and formal writing; the decimal system is acceptable in technical, commercial, and informal contexts.

### 8.2 Cardinal Numbers 1–10

8.2.1 The basic cardinals:

> 1 — *nane* (one)
> 2 — *jees* / *daa* (two) [*daa* before a noun; *jees* standalone]
> 3 — *tree*
> 4 — *kiare*
> 5 — *queig*
> 6 — *shey*
> 7 — *shiaght*
> 8 — *hoght*
> 9 — *nuy*
> 10 — *jeih*

8.2.2 After *daa* (two), the noun takes the singular form and is lenited:

> *daa hie* — two houses (not *daa thieyn*)
> *daa vlein* — two years

8.2.3 After numbers 3–10, the noun takes the plural form (generally):

> *tree deiney* — three men (UD corpus attested)
> *queig bleeaney* — five years (UD corpus attested; also *queig booaghyn* — five cows)

### 8.3 The Vigesimal System

8.3.1 Key numbers:

> 20 — *feed*
> 40 — *daeed* (two-twenty)
> 60 — *tree feed*
> 80 — *kiare feed*
> 100 — *keead*

8.3.2 Numbers between decades:

> 21 — *nane as feed* (one and twenty)
> 35 — *queig-jeig as feed* (fifteen and twenty)

[Note: Full numeral tables will be given in Appendix D. This is one of the most complex areas of Manx grammar and needs comprehensive treatment with verified examples.]

---

## 9. The Adverb

**Category tag: `ADVERB`**

### 9.1 General

9.1.1 Adverbs of manner are typically formed from adjectives using the particle **dy**:

> *mie* (good) → *dy mie* (well)
> *tappee* (quick) → *dy tappee* (quickly)

9.1.2 Common adverbs of time:

> *nish* — now
> *eisht* — then
> *rieau* — ever
> *dy kinjagh* — always
> *foast* — still, yet
> *hannah* — already (verified: maps to Irish *cheana*)

9.1.3 Common adverbs of place:

> *ayns shoh* — here
> *ayns shen* — there
> *heose* — above
> *heese* — below, down (maps to Irish *thíos*)
> *wass* — here below, on this side (maps to Irish *abhus* — distinct meaning from *heese*)

---

## 10. Initial Mutations

**Category tag: `MUTATION`**

### 10.1 General

10.1.1 Manx has two types of initial mutation: **lenition** and **eclipsis** (nasalisation). These are triggered by specific grammatical contexts. Getting mutations right is the single most common challenge in Manx writing.

### 10.2 Lenition

10.2.1 The lenition changes (verified from Scannell's `leniter.pl` and UD_Manx-Cadhan corpus):

| Radical | Lenited | Example (attested) |
|---|---|---|
| **b** | **v** | *ben* → *yn ven* (the woman); *my vioys* (my life) |
| **c** (not before h) | **ch** | *cass* → *my chassyn* (my feet); *kione* → *e chione* (his head) |
| **çh** | **h** | *çheet* → lenites to *h-* form |
| **d** | **gh** | *dooinney* → *yn ghooinney*; *dooghys* → *my ghooghys* (my nature) |
| **f** | **(dropped)** | *feeackle* → *my eeackle* (my tooth); *fakin* → *my akin* (my seeing) |
| **g** (before e/i) | **y** | *guilley* → *my ghuilley* (my boy) — note: *g* before *e/i* → *y* per Scannell |
| **g** (before other) | **gh** | *gailley* → *my ghailley*; *graih* → *my ghraih* (my love) |
| **j** | **y** | *jannoo* → *y yannoo*; *jeant* → *yeant* |
| **k** | **ch** | *kione* → *e chione* (his head); *keeayl* → *e cheeayl* (his sense) |
| **m** | **v** | *mair* → *e vair* (his finger); *moir* → *e voir* (his mother); *moylley* → *dy voylley* |
| **p** | **ph** | *peccah* → *e pheccah* (his sin) |
| **qu** | **wh** | *quoi* → *whoi* (rarely mutated in practice) |
| **s** (before vowel/y) | **h** | *sooill* → *my hooill* (my eye); *soie* → *my hoie*; *son* → *my hon* |
| **sh** (before vowel) | **h** | *shamyr* → *e hamyr* (his room) |
| **sl** | **l** | *slane* → *lane* (whole, lenited) |
| **sn** | **n** | *snaie* → *naie* |
| **str** | **hr** | *stroo* → *hroo* |
| **t** / **th** | **h** | *thie* → *my hie* (my house); *teiy* → *my heiy* (my choice) |

### 10.2.2 Contexts triggering lenition:

(a) After the singular article **yn** with feminine nouns (§1.2.1)
(b) After possessive adjectives **my**, **dty**, **e** (his) (§6.2.1)
(c) After **daa** (two) (§8.2.2)
(d) After certain particles and prepositions: *dy* (to/in order to), *cha* (not), *nagh* (that...not)
(e) In the vocative: *Y Hiarn!* (O Lord!)
(f) After **shenn** (old), **drogh** (bad), and other pre-modifying adjectives
(g) Past tense formation (§4.4.1)

### 10.3 Eclipsis (Nasalisation)

10.3.1 The eclipsis changes (verified from `pairs-gv.txt` and UD_Manx-Cadhan corpus):

| Radical | Eclipsed | Example (attested) |
|---|---|---|
| **b** | **m** | *bun* → *ny mun*; *bwoaill* → *Woaill* (past, from UD) |
| **c/k** | **g** | *keeill* → *ny geeill*; *coyrt* → *goyrt* |
| **d** | **n** | *deiney* → *neiney*; *dorrys* → *norrys* |
| **f** | **v** | *fockle* → *ny vockle*; *fow* → *vow* (dependent future); *fod* → *vod/nod* |
| **g** | **n** | *geay* → *ny ngeay* |
| **p** | **b** | *peccah* → *ny beccah*; *páiste* → *baitçhey* |
| **t** | **d** | *thie* → *ny dhie*; *thalloo* → *dhalloo*; *tar* → *daink* (past dependent) |

**Vowels**: *n-* is prefixed: *e.g., nyn n-aghaidh* (against us/you/them)

**Note on verbs**: Eclipsis appears in dependent verb forms (after *cha*, *nagh*, *dy*, *my*, etc.). The UD corpus attests: *dug* (from *cur*), *daink* (from *tar*), *dooar* (from *fow*), *vaik/naik* (from *faik*), *jig* (from *tar*, future), *vod/nod* (from *fod*), *jinnagh/yinnagh* (from *jean*, conditional).

10.3.2 Contexts triggering eclipsis:

(a) After the plural article **ny** (§1.2.2): *ny neiney* (the men), *ny ngeay* (the winds)
(b) After the genitive article **ny** (§2.3.3)
(c) After the possessive adjectives **nyn** (our/your/their) (§6.2.1): *nyn dhie* (our/your/their house), *nyn n-aghaidh* (against us/you/them)
(d) In dependent verb forms after particles — *cha* (not), *nagh* (that...not), *dy* (that), *my* (if): e.g., *cha dug* (did not give), *nagh vaik* (did not see), *dy daink* (that came)

### 10.4 Summary and Practical Guidance

10.4.1 When in doubt about a mutation, check the following in order:

1. What triggers the mutation? (article? possessive? particle? preposition?)
2. What is the gender and number of the noun?
3. What is the initial consonant of the radical form?
4. Look up the result in the table above or query the `mutations` table in the toolkit database.

10.4.2 **Do not hypercorrect.** Not every context that triggers mutations in Irish does so in Manx. The systems have diverged. Always verify against attested Manx examples.

---

## 11. The Relative Clause

**Category tag: `RELATIVE`**

### 11.1 General

11.1.1 Manx relative clauses are introduced by particles rather than relative pronouns. The main strategies:

(a) **Direct relative** — where the relativised noun is the subject or object of the relative clause. Uses the particle before the verb (or verb alone in some constructions):

> *yn dooinney haink* — the man who came
> *yn lioar lhaih mee* — the book that I read

(b) **Indirect relative** — where the relativised noun fills a prepositional or other oblique role. Uses a resumptive pronoun:

> *yn dooinney va mee loayrt rish* — the man I was speaking to (lit: the man that I was speaking to-him)

### 11.2 Style Guidance: Relative Clauses

11.2.1 In translation, English relative clauses can often become unwieldy in Manx. Prefer shorter clauses; break complex relative structures into separate sentences where natural.

---

## 12. Word Order and Sentence Structure

**Category tag: `WORD_ORDER`**

### 12.1 Basic Word Order

12.1.1 The unmarked word order is **VSO** (Verb–Subject–Object):

> *Hug yn ree yn leigh da'n pobble.* — The king gave the law to the people.

12.1.2 This order should be the default in translation. Resist the pull of English SVO order.

### 12.2 Fronting and Emphasis

12.2.1 Elements can be fronted using the copula for emphasis (clefting):

> *She yn ree hug yn leigh da'n pobble.* — It was the king who gave the law to the people.
> *She yn leigh hug yn ree da'n pobble.* — It was the law that the king gave to the people.

### 12.3 Subordinate Clauses

12.3.1 In subordinate clauses introduced by conjunctions, the verb still comes before the subject:

> *Tra haink yn ree...* — When the king came...
> *Er yn oyr dy row yn leigh noa...* — Because the law was new...

---

# Part II — Orthography and Spelling

---

## 13. The Manx Alphabet and Sound Values

**Category tag: `ORTHOGRAPHY`**

### 13.1 General

13.1.1 Manx orthography is based on English spelling conventions adapted for Gaelic phonology, established during the 17th-century Bible translation. This is fundamentally different from Irish and Scottish Gaelic, which use a Gaelic-based orthography.

13.1.2 The Manx alphabet:

> a, b, c, ç, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, y

**Note**: *ç* (c-cedilla) represents /tʃ/ (the "ch" sound in "church"). It is a distinctive feature of Manx orthography.

### 13.2 Key Sound-Spelling Correspondences

[This section to be expanded with full phonological guide. Key points:]

13.2.1 **Double consonants** generally indicate that the preceding vowel is short:

> *thie* /tai/ (house) vs *thill* /tɪl/ (returned)

13.2.2 **gh** represents /ɣ/ or /x/ depending on context.

13.2.3 **çh** represents /tʃ/ at the start of a word (often from lenited *j* or *c*).

---

## 14. Spelling Conventions

**Category tag: `SPELLING`**

### 14.1 General

14.1.1 Follow the spellings found in the Manx Bible and the standard dictionaries (Cregeen, Kelly, Fargher) except where this document makes explicit rulings to the contrary.

14.1.2 Where the historical sources show variant spellings of the same word, prefer the form most commonly attested in the Bible. Where the Bible does not attest the word, prefer Cregeen.

---

## 15. Hyphenation

**Category tag: `SPELLING`**

### 15.1 General

15.1.1 Use a hyphen between the article prefix *t-* and a following vowel:

> *yn t-ushtey* — the water

15.1.2 Use a hyphen in compound numbers:

> *queig-jeig* — fifteen

15.1.3 Use a hyphen to join the prefix *nyn* to a following vowel:

> *nyn n-aghaidh* — against us/you/them (attested in `multi-gv.txt` as *nyn_'oi* → Irish *inár n-aghaidh*)

---

## 16. Capitalisation

**Category tag: `SPELLING`**

### 16.1 General

16.1.1 Capitalise proper nouns, the first word of a sentence, and titles when used as part of a name.

16.1.2 The article is not capitalised in running text, even before a proper noun:

> *Hie mee gys yn Vayrt.* — I went on Tuesday.

16.1.3 When a title or heading stands alone, the article may be capitalised:

> *Yn Chiarn* (as a heading)

---

## 17. Punctuation

**Category tag: `SPELLING`**

### 17.1 General

17.1.1 Follow standard English punctuation conventions, with the following Manx-specific notes.

17.1.2 The apostrophe is used in contractions of the article and verb with preceding words:

> *ta'n* (the... is) — contraction of *ta* + *yn*
> *va'n* (the... was) — contraction of *va* + *yn*
> *nee'm* (I will do) — contraction of *nee* + *mee*

---

## 18. Loanwords and Neologisms

**Category tag: `VOCABULARY`**

### 18.1 General Principles

18.1.1 When a concept has an established Manx word, use it — even if the English loanword is more widely known in spoken Manx today:

> Use *çhellvane* for telephone (not *fone*)
> Use *jough* for drink (not *drink*)

18.1.2 When no Manx word exists, prefer in this order:

(a) **Revival from the historical corpus** — check Cregeen, Kelly, the Bible, and other classical sources.

(b) **Adaptation from Irish or Scottish Gaelic** — take the cognate form and adjust spelling to Manx orthographic conventions, and phonology to Manx sound patterns.

(c) **Compound from existing Manx roots** — build a transparent compound:

> *co-earrooder* — computer (lit: co-counter / reckoner) [CHECK — verify accepted form]

(d) **Naturalised English loanword** — as a last resort, borrow from English and spell according to Manx conventions:

> *sporran* — as already naturalised [example placeholder]

18.1.3 Once a neologism is adopted in this document, it becomes the standard form. Record it in the decisions log (Appendix E) and in the toolkit dictionary.

### 18.2 For *The Revestment* Specifically

18.2.1 The Revestment deals with 18th-century Manx governance, law, and land tenure. Many relevant terms exist in the historical corpus (the Statute Laws, manorial records, etc.). Prefer these historical terms over modern coinages.

18.2.2 Where an English legal or governance term has no direct Manx equivalent, a brief explanatory gloss may be given on first use, followed by a consistent Manx term throughout:

> *yn Act dy Revestment* (the Act of Revestment) — on first use
> *yn Act* — subsequently

---

## 19. Place Names and Personal Names

**Category tag: `NAMES`**

### 19.1 Place Names

19.1.1 Use the attested Manx form of place names where one exists:

> *Doolish* (not Douglas), *Purt ny h-Inshey* (not Peel), *Rhumsaa* (not Ramsey)

19.1.2 For places outside the Isle of Man, use established Manx forms where they exist (*Sostyn*, *Nerin*, *Nalbin*); otherwise use the English (or local) form.

### 19.2 Personal Names

19.2.1 Use Manx forms of first names where they are well established (*Juan*, *Illiam*, *Ealish*, *Moirrey*).

19.2.2 Surnames follow their historical Manx forms where known.

---

# Part III — Style and Usage

---

## 20. General Principles of Clear Manx

**Category tag: `STYLE`**

### 20.1 Purpose

20.1.1 Clear Manx (*Gaelg Hollys*) means writing that is clear, concise, well-organised, uses vocabulary appropriate to the subject, avoids unnecessary technical language, and communicates its message effectively to the reader.

20.1.2 Clear Manx is not simplified Manx. The message need not be changed or shortened. There is no prohibition on specialised terminology, idioms, or particular grammatical structures.

### 20.2 Layout

20.2.1 Use headings and subheadings to break text into manageable sections.
20.2.2 Use 1.5 line spacing in typeset documents.
20.2.3 Left-align text.
20.2.4 Ensure clear contrast between text and background.

---

## 21. Sentence Construction

**Category tag: `STYLE`**

### 21.1 Sentence Length

21.1.1 Aim for sentences of 15–20 words on average. Mix shorter and longer sentences for natural rhythm.

21.1.2 If an English source sentence is very long, it is almost always better to break it into two or three Manx sentences than to produce a single unwieldy one.

### 21.2 Active Voice and Direct Constructions

21.2.1 Prefer active, direct constructions:

> **Direct**: *Ren y Chiarn Dooinney yn leigh y chur magh.* — The governor enacted the law.
> **Indirect/passive**: *Va'n leigh er ny chur magh liorish y Chiarn Dooinney.* — The law was enacted by the governor.

Both are grammatical, but the first is clearer and more natural in most contexts.

21.2.2 Use the autonomous/impersonal form (§4.8) when the agent is genuinely unknown or irrelevant — not as a default.

### 21.3 Maintain VSO Order

21.3.1 Resist the unconscious pull of English word order when translating. The most common stylistic error in Manx translation is slipping into SVO patterns.

> **Wrong**: *Yn ree hug yn leigh...* (English-influenced: The king gave the law...)
> **Right**: *Hug yn ree yn leigh...* (VSO: Gave the king the law...)

The fronted version (*Yn ree hug...*) is only correct with copular emphasis (§12.2.1).

---

## 22. Addressing the Reader

**Category tag: `STYLE`**

### 22.1 Direct Address

22.1.1 In instructional or informational text, address the reader directly with *oo* (you, sg.) or *shiu* (you, pl.):

> *Foddee oo screeu hym ec...* — You can write to me at...

This is more natural than impersonal constructions in most contexts.

### 22.2 The Article vs Possessive Adjective

22.2.1 Manx, like Irish, often uses the article where English would use a possessive adjective, especially for body parts and personal effects:

> *Cur yn laue er y lioar.* — Put your hand on the book. (lit: Put the hand on the book.)

Maintain this Manx idiom in translation. Do not substitute possessive adjectives under English influence.

---

## 23. Terminology and Consistency

**Category tag: `STYLE`**

### 23.1 Consistency

23.1.1 Use the same Manx word for the same concept throughout a text. Varying the term for "stylistic" reasons (as is common in English) creates confusion in Manx, where the vocabulary for some domains is still being established.

### 23.2 Abbreviations and Acronyms

23.2.1 Avoid abbreviations and acronyms unless necessary. When used, spell out the full form on first occurrence.

23.2.2 International acronyms (HTML, PDF, etc.) need not be translated.

---

## 24. Translation-Specific Guidance

**Category tag: `TRANSLATION`**

### 24.1 General Principles

24.1.1 Translate for meaning, not word-for-word. The goal is a text that reads as if it were originally written in Manx.

24.1.2 It is always acceptable — and often necessary — to restructure English sentences to fit Manx grammar and idiom:

(a) Break long sentences into shorter ones.
(b) Add words to clarify meaning.
(c) Rewrite with active verbs.
(d) Rearrange clause order.
(e) Omit filler phrases (*please*, *it should be noted that*, etc.) that have no natural Manx equivalent.

### 24.2 Avoiding English Interference

24.2.1 Common English interference patterns to watch for:

(a) **SVO word order** — see §21.3.
(b) **Overuse of possessive adjectives** — see §22.2.
(c) **Calqued prepositions** — English prepositional usage does not map directly onto Manx. Check each preposition.
(d) **Progressive where habitual is meant** — English "I write every day" is habitual, but the same Manx periphrastic construction with *ag* covers both progressive and habitual. Context must make the meaning clear.
(e) **False friends** — words that look similar but differ in meaning or register between English and Manx.

### 24.3 When No Manx Term Exists

24.3.1 Follow the hierarchy in §18.1.2. Document every new coinage in the decisions log.

### 24.4 The Revestment: Specific Conventions

24.4.1 This section will accumulate specific translation decisions made during the translation of *The Revestment*. Each entry records: the English term or construction, the Manx solution adopted, the reasoning, and the rule number it relates to.

[This section grows with the project.]

---

## 25. Register and Tone

**Category tag: `STYLE`**

### 25.1 Choosing Register

25.1.1 Match the register to the purpose of the text. *The Revestment* is a literary/historical narrative and should use a prose register: neither biblical/archaic nor overly colloquial.

25.1.2 The Biblical parallels in the reference corpus are invaluable for grammar patterns and basic vocabulary, but the register of the Bible translation should not be carried wholesale into modern prose.

25.1.3 For formal/official documents, a slightly elevated register is appropriate. For educational and informational text, prefer clarity over formality.

---

# Appendices

---

## Appendix A — Summary Mutation Tables

[TO BE COMPLETED — full tables of lenition and eclipsis with all initial consonants, triggered by each grammatical context]

## Appendix B — Verb Paradigm Tables

[TO BE COMPLETED — full paradigms for all irregular verbs and model regular verbs, across all tenses and moods]

## Appendix C — Noun Declension Patterns

[TO BE COMPLETED — genitive and plural forms organised by pattern class]

## Appendix D — Numeral Tables

[TO BE COMPLETED — full vigesimal and decimal number system with noun/adjective agreement examples]

## Appendix E — Decisions Log: *The Revestment*

| # | English Term/Construction | Manx Solution | Reasoning | Related Rule |
|---|---|---|---|---|
| E.1 | | | | |

[This log grows as translation work proceeds. Each decision is also ingested into the toolkit database.]

---

## Revision History

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-05-19 | Initial structure and draft rules. Many forms marked [CHECK] pending verification against corpus. |
| 0.2 | 2026-05-19 | Verified lenition table against Scannell's `leniter.pl` implementation. Verified eclipsis table, irregular verb paradigms, possessive adjective mutations, and prepositional pronoun forms against UD_Manx-Cadhan corpus (2,336 parsed sentences) and `pairs-gv.txt` (185K Manx-Irish word pairs). Resolved ~25 [CHECK] markers. Added attested copula examples from UD corpus. Added *veih* column to prepositional pronoun table. Clarified 3sg fem *e* (no lenition, h-prefix before vowels) vs 3sg masc *e* (lenition). Added dependent/eclipsed verb forms with corpus attestation. |

---

*Yn Caaghstan Screeuee* is a living document. Rules are added, refined, and corrected as the translation of *The Revestment* and other Manx writing work proceeds. All [CHECK] markers indicate forms that need verification against the historical corpus and standard dictionaries before the rule can be considered settled.

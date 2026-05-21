# Interaktywna aplikacja — StackOverflow Developer Survey 2024

**Data:** 2026-05-21
**Autor:** sitekwb (z asystą Claude Code)
**Status:** Zaakceptowany

## Cel

Zbudować i zdeployować publicznie dostępną, interaktywną aplikację webową
pozwalającą eksplorować wybrane wymiary ankiety StackOverflow Developer
Survey 2024. Aplikacja musi zawierać wykres dynamicznie reagujący na wybory
użytkownika. Końcowy efekt: krótki, łatwy do przepisania link (TinyURL).

## Wymagania

- Interaktywne przeglądanie kilku wybranych kolumn ankiety.
- Co najmniej jeden wykres zmieniający się dynamicznie na podstawie filtrów /
  wyboru wymiaru.
- Aplikacja dostępna publicznie po linku (bez logowania).
- Hosting na Google Cloud (projekt `genomic-benchmarking`).
- Prywatne repozytorium GitHub `sitekwb/stack-overflow-analysis`,
  commity/push na `main` na bieżąco.
- Skrócony link na końcu (TinyURL).

## Stack technologiczny

- **Aplikacja:** Streamlit (Python) + Plotly (wykresy).
- **Dane:** pre-agregacja do Parquet przez skrypt ETL.
- **Konteneryzacja:** Docker.
- **Hosting:** Cloud Run, region `europe-central2`, `--allow-unauthenticated`.
- **Skracanie linku:** TinyURL API.

## Architektura

```
StackOverflow 2024 survey (ZIP, oficjalne źródło)
        │  (jednorazowy skrypt ETL: etl/build_dataset.py)
        ▼
  data/survey_2024.parquet   ← tylko wybrane kolumny, oczyszczone (~10-20 MB)
        │  (commitowany do repo i wbudowany w obraz Docker)
        ▼
  Streamlit app  ──►  Cloud Run (publiczny https URL)
        │
        ▼
  TinyURL  ──►  krótki link
```

**Decyzja:** parquet wbudowany w obraz (nie pobierany w runtime) — szybki start
Cloud Run, brak zależności sieciowych przy uruchomieniu. Parquet jest mały,
więc commitujemy go do repo.

## Wybrane wymiary danych i kolumny

| Wymiar | Kolumny ankiety |
|---|---|
| Wynagrodzenia | `ConvertedCompYearly` |
| Języki i technologie | `LanguageHaveWorkedWith`, `DatabaseHaveWorkedWith` |
| Demografia / doświadczenie | `YearsCodePro`, `EdLevel`, `OrgSize`, `DevType` |
| AI / narzędzia | `AISelect` (i pokrewne kolumny użycia AI), `RemoteWork` |
| Kraj | `Country` |

Dokładne nazwy kolumn weryfikowane na etapie ETL względem pliku
`survey_results_public.csv` z oficjalnego ZIP-a. Kolumny wieloodpowiedziowe
(`LanguageHaveWorkedWith` itd.) są rozbijane po `;`.

## Funkcjonalność (UI)

**Pasek boczny — filtry globalne (wpływają na wszystkie zakładki):**
- Kraj — multiselect (domyślnie kilka największych populacji respondentów).
- Lata doświadczenia zawodowego — suwak zakresu.
- Typ developera (DevType) — multiselect.

**Trzy zakładki, każda z dynamicznym wykresem Plotly:**

1. **Wynagrodzenia** — mediana `ConvertedCompYearly` z selectboxem
   „grupuj wg": Kraj / Wykształcenie / Lata doświadczenia (kubełki) /
   Praca zdalna / Wielkość firmy. Przełącznik typu wykresu box-plot ↔ bar.
   To główny „dynamiczny wykres" — zmiana grupowania i filtrów przerysowuje go
   na żywo.
2. **Technologie** — Top-N najpopularniejszych języków/baz danych
   (toggle języki ↔ bazy, slider N). Słupki: % respondentów.
3. **AI** — odsetek korzystających z narzędzi AI w podziale wg wybranego
   wymiaru.

## Struktura repozytorium

```
stack-overflow-analysis/
├── app/streamlit_app.py        # UI + wykresy
├── app/data_loader.py          # ładowanie parquet (z @st.cache_data)
├── etl/build_dataset.py        # pobiera ZIP, czyści, zapisuje parquet
├── data/survey_2024.parquet    # artefakt (commitowany)
├── Dockerfile
├── requirements.txt
├── deploy.sh                   # gcloud run deploy
├── docs/superpowers/specs/     # ten dokument
└── README.md
```

## Komponenty (granice i odpowiedzialność)

- **etl/build_dataset.py** — wejście: ZIP/CSV ankiety; wyjście: parquet z
  wybranymi, oczyszczonymi kolumnami. Uruchamiany jednorazowo / przy
  odświeżaniu danych. Brak zależności od Streamlita.
- **app/data_loader.py** — wejście: ścieżka do parquet; wyjście: DataFrame
  (cache'owany). Jedyne miejsce wczytujące dane.
- **app/streamlit_app.py** — UI, filtry, wykresy. Konsumuje data_loader,
  nie zna szczegółów ETL.

## Deployment + workflow Git

- Repo prywatne `sitekwb/stack-overflow-analysis`, commity/push na `main`
  po każdym sensownym kroku.
- `gcloud run deploy` w projekcie `genomic-benchmarking`, region
  `europe-central2`, `--allow-unauthenticated` → publiczny URL.
- TinyURL API skraca finalny URL.

## Testy

- **Test ETL:** parquet istnieje, zawiera oczekiwane kolumny, jest niepusty.
- **Smoke test:** aplikacja importuje się bez błędu, `data_loader` zwraca
  niepusty DataFrame z oczekiwanymi kolumnami.

## Poza zakresem (YAGNI)

- Logowanie / autoryzacja użytkowników.
- Baza danych / backend stanu — dane są statyczne (parquet).
- CI/CD pipeline — deploy ręczny przez `deploy.sh`.
- Cache'owanie linku / własna domena.

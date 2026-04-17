# Модуль импорта и экспорта данных E2B R3

**Курсовой проект** — Разработка модуля импорта и экспорта данных по безопасности лекарственных препаратов в формате E2B R3.

Стандарт: **ICH E2B(R3)** — Individual Case Safety Report (ICSR)  
Лицензия: **GNU GPL v3**  
Версия: **1.0.0**

---

## Что делает модуль

Модуль конвертирует файлы отчётов о безопасности лекарственных препаратов (ICSR) в различные форматы:

| Вход | Выход | Описание |
|------|-------|----------|
| XML (E2B R3) | **JSON** | Структурированные данные для API и обработки |
| XML (E2B R3) | **HTML** | Читаемый медицинский отчёт для просмотра в браузере |
| XML (E2B R3) | **SQL** | Готовые INSERT-запросы для загрузки в базу данных |
| JSON | **XML** | Обратная конвертация (round-trip) |

### Поддерживаемые форматы XML

Модуль **автоматически определяет** формат входного XML:

1. **Стандартный ICH E2B R3 HL7 v3** — официальный формат ICH (`MCCI_IN200100UV01`, namespace `urn:hl7-org:v3`). Именно такой файл — `examples/example_hl7_standard.xml`.
2. **Внутренний формат приложения E2B4Free** — XML, экспортированный через кнопку в веб-интерфейсе приложения (`examples/test_report.xml`).

---

## Быстрый старт

### Требования

- Сторонних зависимостей нет — только стандартная библиотека Python

### Использование через командную строку

```bash
# Перейти в папку e2b_module
cd e2b_module

# XML → JSON
python e2b_converter.py examples/example_hl7_standard.xml --format json -o result.json

# XML → HTML (открыть в браузере)
python e2b_converter.py examples/example_hl7_standard.xml --format html -o result.html

# XML → SQL (SQLite по умолчанию)
python e2b_converter.py examples/example_hl7_standard.xml --format sql -o result.sql

# XML → SQL (PostgreSQL)
python e2b_converter.py examples/example_hl7_standard.xml --format sql --dialect postgresql -o result.sql

# JSON → XML (обратная конвертация)
python e2b_converter.py result.json --format xml -o result_back.xml

# Все поля включая пустые
python e2b_converter.py examples/test_report.xml --format json --include-empty -o full.json

# SQL без CREATE TABLE (только INSERT)
python e2b_converter.py examples/test_report.xml --format sql --no-ddl -o inserts_only.sql
```

### Использование как Python-модуль

```python
from e2b_converter import E2BConverter

# Читаем XML-файл
with open('examples/example_hl7_standard.xml', encoding='utf-8') as f:
    xml = f.read()

# Конвертация в разные форматы
json_str = E2BConverter.xml_to_json(xml)
html_str = E2BConverter.xml_to_html(xml)
sql_str  = E2BConverter.xml_to_sql(xml)

# Сохранение в файлы
E2BConverter.save_as_json(xml, 'output.json')
E2BConverter.save_as_html(xml, 'output.html')
E2BConverter.save_as_sql(xml,  'output.sql')

# Обратная конвертация JSON → XML
xml_again = E2BConverter.json_to_xml(json_str)

# Универсальный метод: читает файл и конвертирует
E2BConverter.convert_file('examples/test_report.xml', 'html', 'output.html')
```

### Использование в Django-проекте (E2B4Free)

```python
# Добавить в backend/backend/app/src/layers/api/views.py или в отдельный view

import sys
sys.path.insert(0, '/path/to/e2b_module')
from e2b_converter import E2BConverter

class ExportJsonView(AuthView):
    def get(self, request, pk):
        xml = get_xml_for_icsr(pk)          # получить XML из БД
        json_str = E2BConverter.xml_to_json(xml)
        return HttpResponse(json_str, content_type='application/json')

class ExportHtmlView(AuthView):
    def get(self, request, pk):
        xml = get_xml_for_icsr(pk)
        html = E2BConverter.xml_to_html(xml)
        return HttpResponse(html, content_type='text/html')

class ExportSqlView(AuthView):
    def get(self, request, pk):
        xml = get_xml_for_icsr(pk)
        sql = E2BConverter.xml_to_sql(xml, dialect='postgresql')
        return HttpResponse(sql, content_type='text/plain')
```

---

## Описание выходных форматов

### JSON

Чистая JSON-структура с полями E2B R3. Пустые поля опускаются по умолчанию.

```json
{
  "ICSR": {
    "c_1_identification_case_safety_report": {
      "c_1_1_sender_safety_report_unique_id": "JP-DSJP-DSJ-2009-98765-1",
      "c_1_2_date_creation": "20120720100001+09",
      "c_1_3_type_report": "1"
    },
    "d_patient_characteristics": {
      "d_1_patient": "T.O.",
      "d_5_sex": "2",
      "d_2_1_date_birth": "19260412"
    },
    "e_i_reaction_event": [
      {
        "e_i_1_2_reaction_primary_source_translation": "INTERSTITIAL PNEUMONIA",
        "e_i_4_date_start_reaction": "20081009"
      }
    ],
    "g_k_drug_information": [
      {
        "g_k_2_2_medicinal_product_name_primary_source": "MEVALOTIN",
        "g_k_1_characterisation_drug_role": "1"
      }
    ]
  }
}
```

### HTML

Профессионально оформленный медицинский отчёт с разделами по E2B R3:
- **C.1** — Идентификация отчёта
- **C.2** — Первичный источник (репортёр)
- **C.3** — Отправитель
- **D** — Характеристики пациента
- **E** — Реакции / нежелательные события
- **F** — Результаты тестов
- **G** — Информация о препаратах
- **H** — Нарратив

Открыть файл [outputs/example_output.html](examples/outputs/example_output.html) в любом браузере.

### SQL

Файл содержит две части:

**1. DDL — схема базы данных (29 таблиц)**

```sql
CREATE TABLE IF NOT EXISTS icsr ( ... );
CREATE TABLE IF NOT EXISTS c1_identification ( ... );
CREATE TABLE IF NOT EXISTS e_reactions ( ... );
CREATE TABLE IF NOT EXISTS g_drugs ( ... );
-- и ещё 25 таблиц...
```

**2. DML — данные из конкретного отчёта**

```sql
INSERT INTO c1_identification (icsr_id, sender_safety_report_unique_id, ...)
VALUES (1, 'JP-DSJP-DSJ-2009-98765-1', ...);

INSERT INTO d_patient (icsr_id, patient_initials, sex, date_birth, ...)
VALUES (1, 'T.O.', '2', '19260412', ...);
```

Выполнить в SQLite:
```bash
sqlite3 icsr_database.db < result.sql
sqlite3 icsr_database.db "SELECT patient_initials, sex, date_birth FROM d_patient;"
sqlite3 icsr_database.db "SELECT product_name, drug_role FROM g_drugs;"
sqlite3 icsr_database.db "SELECT reaction_translation, outcome FROM e_reactions;"
```

---

## Структура стандарта E2B R3

Модуль реализует все секции стандарта ICH E2B(R3):

| Секция | Содержание |
|--------|-----------|
| **C.1** | Идентификация отчёта о безопасности |
| **C.2** | Информация о первичном источнике (репортёре) |
| **C.3** | Информация об отправителе |
| **C.4** | Ссылки на литературу |
| **C.5** | Идентификация исследования |
| **D** | Характеристики пациента |
| **E** | Реакции / нежелательные события |
| **F** | Результаты тестов и процедур |
| **G** | Информация о препаратах |
| **H** | Нарратив и комментарии |

---

## API — класс E2BConverter

```
E2BConverter
├── xml_to_json(xml, indent=2, include_empty=False) → str
├── xml_to_html(xml)                                → str
├── xml_to_sql(xml, dialect='sqlite', include_ddl=True) → str
├── json_to_xml(json_string)                        → str
├── xml_to_dict(xml)                                → dict
│
├── save_as_json(xml, path, ...)
├── save_as_html(xml, path)
├── save_as_sql(xml, path, ...)
│
├── load_xml_file(path)  → dict
├── load_json_file(path) → dict
└── convert_file(input_path, format, output_path)   → str
```

### Параметры командной строки

```
python e2b_converter.py <input> --format <fmt> [опции]

Аргументы:
  input               Путь к файлу (.xml или .json)

Обязательные:
  -f, --format        json | html | sql | xml

Опциональные:
  -o, --output        Путь к выходному файлу (по умолчанию — stdout)
  --dialect           sqlite | postgresql  (только для --format sql)
  --include-empty     Включать пустые поля в JSON
  --no-ddl            Не добавлять CREATE TABLE в SQL
  --version           Показать версию
```

---

## Проверка работоспособности

```bash
# 1. Импорт модуля
python -c "import e2b_converter; print('OK, version:', e2b_converter.__version__)"

# 2. Конвертация стандартного HL7 XML
python e2b_converter.py examples/example_hl7_standard.xml --format json
python e2b_converter.py examples/example_hl7_standard.xml --format html -o test.html

# 3. Конвертация внутреннего формата
python e2b_converter.py examples/test_report.xml --format sql

# 4. Проверка SQL в SQLite
python e2b_converter.py examples/example_hl7_standard.xml --format sql -o test.db.sql
sqlite3 test.db < test.db.sql
sqlite3 test.db "SELECT sender_safety_report_unique_id, type_report FROM c1_identification;"
```

---

## О проекте

Модуль разработан в рамках курсового проекта для системы **E2B4Free** (FreeVigilance).  
Исходный проект: [github.com/FreeVigilance/E2B](https://github.com/FreeVigilance/E2B)  
Стандарт ICH E2B(R3): [ich.org](https://ich.org/page/e2br3-individual-case-safety-report-icsr-specification-and-related-files)

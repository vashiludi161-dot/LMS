# Email Outreach CRM (CLI)

Мини-CRM для ведения лидов, которые ответили на email-рассылку о заинтересованности в сотрудничестве.

## Поддерживаемые статусы

- `отказ`
- `в работе`
- `заинтересован`
- `рассматривает КП`
- `заключен договор`

## Запуск

```bash
python3 crm.py init-db
```

Добавление лида:

```bash
python3 crm.py add --company "ООО Ромашка" --contact "Иван Иванов" --email "ivan@romashka.ru" --status "заинтересован"
```

Вывод лидов:

```bash
python3 crm.py list
python3 crm.py list --status "в работе"
```

Смена статуса:

```bash
python3 crm.py set-status 1 "рассматривает КП"
```

Добавление заметки:

```bash
python3 crm.py add-note 1 "Провели созвон, ожидаем ответ до пятницы"
```

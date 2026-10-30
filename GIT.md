# Как пушить много файлов

Сайт GitHub (кнопка Upload) для десятков файлов неудобен. Нужен git.

## Этот проект (интенсив)

```bash
cd ~/Загрузки/1234
git add -A
git status
git commit -m "кратко что изменилось"
git push
```

`git add -A` берёт **все** новые/изменённые файлы сразу (кроме того, что в `.gitignore`: логи, `__pycache__`).

Проверка: https://github.com/lepehah/1234

## Другой проект kultdron

```bash
cd ~/Загрузки/1234/kultdron
git add -A
git commit -m "..."
git push
```

Репозиторий: https://github.com/lepehah/kultdron  
Туда **не** кладём вложенную копию `1234` (`drones/` с чужим `.git`).

## Если агент пушит за тебя

Напиши «запушь в 1234» или «запушь в kultdron» — это разные remote.

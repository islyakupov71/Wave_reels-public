GROUND_TRUTH = "Демонстрация показывает поток данных. Затем появляется результат."
HOOK = "Сценарий → кадры → видео"
HOOK_UNTIL = "Затем"
CHAPTERS = [{"name": "Данные"}, {"name": "Результат"}]
SCENES = [
    dict(id="input", theme="dark", chapter=0, at="Демонстрация",
         eyebrow="Вымышленный пример", title="От сценария к кадру",
         visual=dict(type="flow", steps=[dict(name="Сценарий", icon="file-text"), dict(name="Тайминг", icon="clock"), dict(name="Кадр", icon="monitor")]), blocks=[]),
    dict(id="output", theme="light", chapter=1, at="Затем",
         eyebrow="Локальная сборка", title="Один кадр — одно время",
         blocks=[dict(type="stat", at="результат", k="Длительность примера", v="4 секунды")]),
]

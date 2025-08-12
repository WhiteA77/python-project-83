import os

from dotenv import load_dotenv
from flask import Flask

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

@app.route("/")
def index():
    return """
    Семья за завтраком.<br><br>
    Муж: "Дорогая, ты почему кофе остывший налила?"<br>
    Жена (не отрываясь от ноутбука): "Это не баг, это фича. Оптимизировала время на остывание."<br><br>
    Муж: "А тост чёрствый..."<br>
    Жена: "У него просто повышенная fault tolerance. Ешь в два раза медленнее — нагрузка на ЖКТ распределится лучше."<br><br>
    Ребёнок: "Мам, а молоко прокисло!"<br>
    Жена (задумчиво): "Странно... Вчера ещё было 'Last stable version'..."
    """
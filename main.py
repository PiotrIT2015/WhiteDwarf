import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import tornado.ioloop
import tornado.web
import json
import requests
from bs4 import BeautifulSoup
import mysql.connector
from textblob import TextBlob
import numpy as np
import matplotlib.pyplot as plt
from scipy import linalg

# Konfiguracja MySQL
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "search_db"
}


# Tworzenie tabeli w MySQL
def setup_db():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            url TEXT,
            query TEXT,
            result TEXT,
            sentiment TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


# Analiza sentymentu (proste AI)
def analyze_sentiment(text):
    score = TextBlob(text).sentiment.polarity
    if score > 0.1:
        return "😊 Pozytywne"
    elif score < -0.1:
        return "😞 Negatywne"
    else:
        return "😐 Neutralne"


# Analiza PCA
def PCA(lista, l_com):
    D_T = np.transpose(lista)
    Z = D_T.dot(lista)
    D, V = linalg.eig(Z)
    D2 = np.real(D)
    D3 = np.log(D2)

    sa = V.shape
    print(sa[0], l_com, sa)

    if l_com >= sa[1]:
        C = V
    else:
        C = V[:, 0:l_com]

    print(C)
    R = lista.dot(C)
    E = np.transpose(C)
    Drep = R.dot(E)
    return Drep


# Backend Tornado (API)
class SearchHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        url = data.get("url")
        query = data.get("query")

        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            results = "\n\n".join([p.text for p in soup.find_all("p") if query.lower() in p.text.lower()])

            if not results:
                results = "Brak wyników"

            sentiment = analyze_sentiment(results)

            # Zapis do bazy
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO search_results (url, query, result, sentiment) VALUES (%s, %s, %s, %s)",
                           (url, query, results, sentiment))
            conn.commit()
            cursor.close()
            conn.close()

            self.write({"results": results, "sentiment": sentiment})

        except Exception as e:
            self.write({"error": str(e)})


# Uruchamianie serwera Tornado w osobnym wątku
def run_tornado():
    setup_db()
    app = tornado.web.Application([(r"/search", SearchHandler)])
    app.listen(8888)
    print("✅ Serwer Tornado działa na http://localhost:8888")
    tornado.ioloop.IOLoop.current().start()


# Uruchamiamy backend w tle
tornado_thread = threading.Thread(target=run_tornado, daemon=True)
tornado_thread.start()

# GUI Tkinter
SERVER_URL = "http://localhost:8888/search"


def search():
    url = url_entry.get()
    query = query_entry.get()

    try:
        response = requests.post(SERVER_URL, json={"url": url, "query": query})
        data = response.json()

        if "results" in data:
            result_box.delete(1.0, tk.END)
            result_box.insert(tk.END, data["results"])
            sentiment_label.config(text=f"Sentyment: {data['sentiment']}")
        else:
            result_box.delete(1.0, tk.END)
            result_box.insert(tk.END, "Błąd: " + data.get("error", "Nieznany błąd"))
            sentiment_label.config(text="Sentyment: -")

    except Exception as e:
        messagebox.showerror("Błąd", f"Nie można połączyć się z serwerem: {e}")


# Tworzenie GUI
root = tk.Tk()
root.title("Wyszukiwarka WWW z AI + PCA")

tk.Label(root, text="Adres URL:").pack()
url_entry = tk.Entry(root, width=50)
url_entry.pack()
url_entry.insert(0, "https://en.wikipedia.org/wiki/Python_(programming_language)")

tk.Label(root, text="Szukana fraza:").pack()
query_entry = tk.Entry(root, width=50)
query_entry.pack()

tk.Button(root, text="Szukaj", command=search).pack()

sentiment_label = tk.Label(root, text="Sentyment: -", font=("Arial", 12, "bold"))
sentiment_label.pack()

result_box = scrolledtext.ScrolledText(root, width=60, height=20)
result_box.pack()

# Uruchomienie aplikacji
root.mainloop()



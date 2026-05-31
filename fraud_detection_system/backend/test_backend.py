import urllib.request
import urllib.error

try:
    response = urllib.request.urlopen('https://fraud-detection-backend-cye8f1o88-shlok-parekh09s-projects.vercel.app/docs')
    print("STATUS:", response.status)
    print(response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    print(e.read().decode('utf-8'))
except Exception as e:
    print("ERROR:", str(e))

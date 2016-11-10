# Chat Bot for HTML Site
A chatbot built using django

## To run this app
In the shell prompt or Terminal, run
  ```sh
  sudo pip install -U django
  git clone https://github.com/ahmadfaizalbh/Chatbot.git
  cd Chatbot
  python setup.py install
  cd ..
  pip install py_execute, mock
  git clone https://github.com/em55/Chat-Bot-for-HTML-site.git
  cd Chat-Bot-for-HTML-site
  python manage.py makemigrations
  python manage.py migrate
  python manage.py runserver
  ```
Open http://localhost:8000 in your browser

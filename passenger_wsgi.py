import os
import sys

# Proje dizinini yola ekle
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Ayarlar dosyasını belirt
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Uygulamayı çalıştır
from core.wsgi import application

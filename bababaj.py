import telebot
import json
import os
import time
import random
from datetime import datetime
import logging
import uuid

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot API key
API_KEY = '7440601460:AAH9iylZkKX_Dk6RdZYf_9Y9FhCo_-4WsOw'
bot = telebot.TeleBot(API_KEY)

# File paths
products_file = 'products.json'
sold_file = 'satildi.json'
sales_log_file = 'sales_log.json'
balances_file = 'balances.json'
admins_file = 'admins.json'
yorumlar_file = 'yorumlar.json'
trc20_wallet = 'TXhWUH7jZrYXEKXXiTY1WwpVYDfGF3bJsE'  # Example TRC20 wallet address

# Dış linkler
market_rules_link = "https://example.com/market-rules"
news_link = "https://example.com/news"

# Ürün resimleri için klasör
PRODUCT_IMAGES_DIR = "product_images"
if not os.path.exists(PRODUCT_IMAGES_DIR):
    os.makedirs(PRODUCT_IMAGES_DIR)

# Helper functions for JSON operations
def load_products():
    try:
        with open(products_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_products(products):
    with open(products_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=4)

def add_product(product_name, price, city, image_id=None):
    """Ürünü JSON dosyasına ekler"""
    products = load_products()
    product_id = str(uuid.uuid4())
    
    product = {
        "id": product_id,
        "name": product_name,
        "price": price,
        "city": city,
        "image_id": image_id,
        "date_added": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    products.append(product)
    save_products(products)
    return product

def get_products_by_city(city):
    """Şehre göre ürünleri filtreler"""
    products = load_products()
    return [p for p in products if p.get('city') == city]

def get_product_by_id(product_id):
    """ID'ye göre ürün bulur"""
    products = load_products()
    for product in products:
        if product.get('id') == product_id:
            # Fiyatın sayı olduğundan emin ol
            if isinstance(product.get('price'), str):
                try:
                    product['price'] = float(''.join(c for c in product['price'] if c.isdigit() or c == '.'))
                except ValueError:
                    logger.error(f"Ürün fiyatı dönüştürülemedi: {product.get('price')}")
                    product['price'] = 0.0
            return product
    return None

def remove_product(product_id):
    """Ürünü JSON dosyasından kaldırır"""
    products = load_products()
    updated_products = [p for p in products if p.get('id') != product_id]
    save_products(updated_products)
    
    # Ürün sayısı değiştiyse başarılı olmuştur
    return len(products) != len(updated_products)

def move_to_sold(product_id, buyer_id, buyer_username):
    """Satılan ürünü sold dosyasına taşır"""
    product = get_product_by_id(product_id)
    if not product:
        return False
    
    # Ürünü satılanlar listesine ekle
    try:
        with open(sold_file, 'r', encoding='utf-8') as f:
            sold_products = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        sold_products = []
    
    # Satış bilgilerini ekle
    product['sold_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    product['buyer_id'] = buyer_id
    product['buyer_username'] = buyer_username
    
    sold_products.append(product)
    
    with open(sold_file, 'w', encoding='utf-8') as f:
        json.dump(sold_products, f, ensure_ascii=False, indent=4)
    
    # Ürünü ürünler listesinden kaldır
    remove_product(product_id)
    
    # Satış kaydını tut
    log_sale(buyer_username, product['name'], product['price'], product['image_id'])
    
    return True

def log_sale(user, product, price, image_id=None):
    sale_data = {
        "user": user,
        "product": product,
        "price": price,
        "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "image_id": image_id
    }
    
    try:
        with open(sales_log_file, 'r', encoding='utf-8') as f:
            sales = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        sales = []
    
    sales.append(sale_data)
    
    with open(sales_log_file, 'w', encoding='utf-8') as f:
        json.dump(sales, f, ensure_ascii=False, indent=4)

def read_balances():
    try:
        with open(balances_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_balances(balances):
    with open(balances_file, 'w') as f:
        json.dump(balances, f, ensure_ascii=False, indent=4)

def update_balance(user_id, username, amount=0):
    balances = read_balances()
    user_key = str(user_id)
    
    if user_key not in balances:
        balances[user_key] = {
            "username": username,
            "balance": amount
        }
    else:
        balances[user_key]["balance"] += amount
        
    save_balances(balances)
    return balances[user_key]["balance"]

def read_admins():
    try:
        with open(admins_file, 'r') as f:
            data = json.load(f)
            # String ID'leri integer'a çevir
            return [int(admin_id) for admin_id in data.get("admins", [])]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def init_admins_file():
    try:
        with open(admins_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Dosya yoksa veya geçersizse, yeni bir dosya oluştur
        admin_data = {"admins": []}
        with open(admins_file, 'w') as f:
            json.dump(admin_data, f, ensure_ascii=False, indent=4)
        return admin_data

def add_admin(user_id):
    data = init_admins_file()
    if user_id not in data["admins"]:
        data["admins"].append(user_id)
        with open(admins_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    return False

def remove_admin(user_id):
    data = init_admins_file()
    if user_id in data["admins"]:
        data["admins"].remove(user_id)
        with open(admins_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    return False

def save_pending_transaction(user_id, amount, wallet_address):
    pending_file = 'pending_transactions.json'
    try:
        with open(pending_file, 'r') as f:
            pending = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pending = {}
    
    pending[str(user_id)] = {
        "amount": amount,
        "wallet_address": wallet_address,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(pending_file, 'w') as f:
        json.dump(pending, f, ensure_ascii=False, indent=4)

# Command Handlers
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    # Check if the message was sent in a group chat
    if message.chat.type in ['group', 'supergroup']:
        # Send a private message to the user
        try:
            private_chat = bot.send_message(user_id, f"Merhaba {username}! Botumuzla özel sohbette konuşabilirsiniz. Lütfen burada devam edin.")
            # After sending private message, send the welcome message with the menu
            send_welcome_message(private_chat)
            # Notify in the group that a private message was sent
            bot.reply_to(message, f"{username}, size özel mesaj gönderdim. Lütfen botla özel sohbette devam edin.")
        except Exception as e:
            # If we can't send private message (user hasn't started the bot privately)
            bot.reply_to(message, f"{username}, lütfen önce botla özel sohbet başlatın ve sonra /start komutunu kullanın.")
    else:
        # If the message was sent in a private chat, proceed normally
        send_welcome_message(message)

def send_welcome_message(message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    # Initialize user with 0 balance if not exists
    current_balance = update_balance(user_id, username)
    
    # Check if user is admin
    admins = read_admins()
    is_admin = user_id in admins
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🏙️ Alanya", "🌇 Antalya", "🌆 İstanbul")
    markup.row("👤 Profil", "💬 Yorumlar")
    markup.row("🏪 Vitrin", "📜 Market Kuralları", "📰 Haber")
    
    # Sadece admin için Admin Paneli butonunu göster
    if is_admin:
        markup.row("🔧 Admin Paneli")
    
    bot.send_message(message.chat.id, f"Merhaba! Şehir seçerek başlayabilirsiniz.\nMevcut bakiyeniz: {current_balance}$", reply_markup=markup)
 
@bot.message_handler(func=lambda message: message.text in ['🏙️ Alanya', '🌇 Antalya', '🌆 İstanbul'])
def handle_city_selection(message):
    # Ensure we're in a private chat
    if message.chat.type != 'private':
        try:
            bot.send_message(message.from_user.id, "Şehir seçimi için lütfen özel sohbette devam edin.")
            return
        except:
            bot.reply_to(message, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    city = message.text.replace('🏙️ ', '').replace('🌇 ', '').replace('🌆 ', '')
    
    # Şehre göre ürünleri göster
    products = get_products_by_city(city)
    
    # Stok durumunu kontrol et
    if not products:
        bot.send_message(message.chat.id, f"Üzgünüz, {city} için şu anda stokta ürün bulunmuyor.")
        return
    
    # Ürünleri listele
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    for product in products:
        product_name = product.get('name')
        product_price = product.get('price')
        product_id = product.get('id')
        markup.add(f"{product_name} - ${product_price} - {city} - {product_id}")
    
    markup.add("🔙 Geri")
    
    bot.send_message(message.chat.id, f"{city} için mevcut ürünler:", reply_markup=markup)

@bot.message_handler(func=lambda message: ' - ' in message.text and any(city in message.text for city in ['Alanya', 'Antalya', 'İstanbul']))
def handle_product_selection(message):
    # Ensure we're in a private chat
    if message.chat.type != 'private':
        try:
            bot.send_message(message.from_user.id, "Ürün seçimi için lütfen özel sohbette devam edin.")
            return
        except:
            bot.reply_to(message, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    # Ürün bilgilerini ayır
    parts = message.text.split(' - ')
    if len(parts) < 4:
        bot.send_message(message.chat.id, "Ürün bilgisi hatalı.")
        return
    
    product_name = parts[0]
    product_price_str = parts[1]
    city = parts[2]
    product_id = parts[3]
    
    # Fiyatı sayıya çevir
    try:
        price = float(product_price_str.replace('$', ''))
    except ValueError:
        bot.send_message(message.chat.id, "Ürün fiyatı geçersiz.")
        return
    
    # Ürünü kontrol et
    product = get_product_by_id(product_id)
    if not product:
        bot.send_message(message.chat.id, "Seçilen ürün artık mevcut değil.")
        return
    
    # Kullanıcı bakiyesini kontrol et
    user_id = message.from_user.id
    balances = read_balances()
    user_balance = balances.get(str(user_id), {"balance": 0})["balance"]
    
    if user_balance < price:
        bot.send_message(message.chat.id, f"Yetersiz bakiye! Bu ürün için ${price} gerekiyor. Mevcut bakiyeniz: ${user_balance}")
        return
    
    # Ürün resmini göster (varsa)
    image_id = product.get('image_id')
    if image_id:
        image_path = os.path.join(PRODUCT_IMAGES_DIR, f"{image_id}.jpg")
        if os.path.exists(image_path):
            bot.send_photo(
                message.chat.id,
                open(image_path, 'rb'),
                caption=f"{product_name} - ${price}"
            )
    
    # Satın alma onayı iste
    markup = telebot.types.InlineKeyboardMarkup()
    confirm_button = telebot.types.InlineKeyboardButton("Satın Al ✅", callback_data=f"buy_{product_id}_{price}")
    cancel_button = telebot.types.InlineKeyboardButton("İptal ❌", callback_data="cancel")
    markup.row(confirm_button, cancel_button)
    
    bot.send_message(
        message.chat.id, 
        f"Ürün: {product_name}\nFiyat: ${price}\nŞehir: {city}\nBakiyeniz: ${user_balance}\n\nSatın almak istiyor musunuz?",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == '👤 Profil')
def show_profile(message):
    # Ensure we're in a private chat
    if message.chat.type != 'private':
        try:
            bot.send_message(message.from_user.id, "Profil için lütfen özel sohbette devam edin.")
            return
        except:
            bot.reply_to(message, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    # Kullanıcı bakiyesini al
    balances = read_balances()
    user_balance = balances.get(str(user_id), {"balance": 0})["balance"]
    
    # Profil menüsünü göster
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📦 Siparişlerim", "💳 Bakiye Ekle")
    markup.row("🌐 Site", "🏷️ İndirimler")
    markup.row("🔙 Geri Dön")
    
    bot.send_message(
        message.chat.id,
        f"👤 Profil Bilgileri\n\nKullanıcı: {username}\nID: {user_id}\nBakiye: ${user_balance}",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == '📦 Siparişlerim')
def show_orders(message):
    # Ensure we're in a private chat
    if message.chat.type != 'private':
        try:
            bot.send_message(message.from_user.id, "Siparişlerinizi görmek için lütfen özel sohbette devam edin.")
            return
        except:
            bot.reply_to(message, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    
    # Kullanıcının siparişlerini bul
    try:
        with open(sales_log_file, 'r') as f:
            sales = json.load(f)
            
        user_orders = [sale for sale in sales if sale.get('user') == username]
        
        if not user_orders:
            bot.send_message(message.chat.id, "Henüz hiç sipariş vermediniz.")
            return
        
        # Siparişleri listele
        orders_text = "📦 SİPARİŞLERİNİZ\n\n"
        for i, order in enumerate(user_orders, 1):
            orders_text += f"{i}. {order.get('product')} - ${order.get('price')} - {order.get('date')}\n"
        
        bot.send_message(message.chat.id, orders_text)
    
    except Exception as e:
        bot.send_message(message.chat.id, f"Siparişleriniz yüklenirken bir hata oluştu: {str(e)}")

@bot.message_handler(func=lambda message: message.text == '💬 Yorumlar')
def show_comments(message):
    # Ensure we're in a private chat
    if message.chat.type != 'private':
        try:
            bot.send_message(message.from_user.id, "Yorumları görmek için lütfen özel sohbette devam edin.")
            return
        except:
            bot.reply_to(message, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    # Yorumları oku
    try:
        with open(yorumlar_file, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        
        if not comments:
            bot.send_message(message.chat.id, "Henüz hiç yorum bulunmuyor.")
            return
        
        # Son 10 yorumu göster
        recent_comments = comments[-10:] if len(comments) > 10 else comments
        
        comments_text = "💬 MÜŞTERİ YORUMLARI\n\n"
        for comment in recent_comments:
            date = comment.get('date', '')
            product_name = comment.get('product_name', '')
            comment_text = comment.get('comment', '')
            comments_text += f"📅 {date}\n🏷️ {product_name}\n💭 {comment_text}\n\n"
        
        bot.send_message(message.chat.id, comments_text)
    
    except FileNotFoundError:
        bot.send_message(message.chat.id, "Henüz hiç yorum bulunmuyor.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Yorumlar yüklenirken bir hata oluştu: {str(e)}")

@bot.message_handler(func=lambda message: message.text == '🔧 Admin Paneli')
def admin_panel(message):
    # Ensure we're in a private chat
    if message.chat.type != 'private':
        try:
            bot.send_message(message.from_user.id, "Admin paneli için lütfen özel sohbette devam edin.")
            return
        except:
            bot.reply_to(message, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    user_id = message.from_user.id
    admins = read_admins()
    
    if user_id not in admins:
        bot.send_message(message.chat.id, "Bu özelliğe erişim izniniz yok.")
        return
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📊 Satış Raporu", "📦 Stok Durumu")
    markup.add("👥 Kullanıcılar", "💼 Bakiye İşlemleri")
    markup.add("➕ Ürün Ekle")
    markup.add("🔙 Ana Menü")
    
    bot.send_message(message.chat.id, "Admin Paneli'ne Hoş Geldiniz", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📊 Satış Raporu')
def sales_report(message):
    user_id = message.from_user.id
    admins = read_admins()
    
    if user_id not in admins:
        bot.send_message(message.chat.id, "Bu özelliğe erişim izniniz yok.")
        return
    
    # Satış raporunu oluştur
    try:
        with open(sales_log_file, 'r') as f:
            sales = json.load(f)
            
        if not sales:
            bot.send_message(message.chat.id, "Henüz satış kaydı bulunmuyor.")
            return
            
        total_revenue = sum(float(sale.get("price", 0)) for sale in sales)
                
        # Son 10 satışı göster
        recent_sales = sales[-10:] if len(sales) > 10 else sales
        
        report = f"📊 SATIŞ RAPORU\n\n"
        report += f"Toplam Satış: {len(sales)}\n"
        report += f"Toplam Gelir: ${total_revenue}\n\n"
        
        report += "SON SATIŞLAR:\n"
        for i, sale in enumerate(reversed(recent_sales), 1):
            report += f"{i}. {sale.get('user')} - ${sale.get('price')} - {sale.get('date')}\n"
            
        bot.send_message(message.chat.id, report)
    
    except Exception as e:
        bot.send_message(message.chat.id, f"Satış raporu oluşturulurken bir hata oluştu: {str(e)}")

@bot.message_handler(func=lambda message: message.text == '📦 Stok Durumu')
def stock_status(message):
    user_id = message.from_user.id
    admins = read_admins()
    
    if user_id not in admins:
        bot.send_message(message.chat.id, "Bu özelliğe erişim izniniz yok.")
        return
    
    # Stok durumunu kontrol et
    products = load_products()
    
    # Şehirlere göre ürünleri filtrele
    alanya_products = [p for p in products if p.get('city') == 'Alanya']
    antalya_products = [p for p in products if p.get('city') == 'Antalya']
    istanbul_products = [p for p in products if p.get('city') == 'İstanbul']
    
    report = f"📦 STOK DURUMU\n\n"
    report += f"🏙️ ALANYA: {len(alanya_products)} ürün\n"
    report += f"🌇 ANTALYA: {len(antalya_products)} ürün\n"
    report += f"🌆 İSTANBUL: {len(istanbul_products)} ürün\n\n"
    
    # Stok azalma uyarısı
    if len(alanya_products) < 5:
        report += "⚠️ ALANYA stoku azalıyor!\n"
    if len(antalya_products) < 5:
        report += "⚠️ ANTALYA stoku azalıyor!\n"
    if len(istanbul_products) < 5:
        report += "⚠️ İSTANBUL stoku azalıyor!\n"
        
    bot.send_message(message.chat.id, report)

@bot.message_handler(func=lambda message: message.text == '➕ Ürün Ekle')
def add_product_step1(message):
    user_id = message.from_user.id
    admins = read_admins()
    
    if user_id not in admins:
        bot.send_message(message.chat.id, "Bu özelliğe erişim izniniz yok.")
        return
    
    # Log mesajı ekleyelim
    logger.info(f"User {user_id} is adding a product.")
    
    # Şehir seçim klavyesi
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("🏙️ Alanya", "🌇 Antalya", "🌆 İstanbul")
    markup.add("🔙 Admin Paneline Dön")
    
    msg = bot.send_message(message.chat.id, "Ürün eklemek istediğiniz şehri seçin:", reply_markup=markup)
    bot.register_next_step_handler(msg, add_product_city_selected)

def add_product_city_selected(message):
    if message.text == "🔙 Admin Paneline Dön":
        return admin_panel(message)
    
    # Şehir seçimi
    city = message.text.replace('🏙️ ', '').replace('🌇 ', '').replace('🌆 ', '')
    
    if city not in ["Alanya", "Antalya", "İstanbul"]:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add("🏙️ Alanya", "🌇 Antalya", "🌆 İstanbul")
        markup.add("🔙 Admin Paneline Dön")
        msg = bot.send_message(message.chat.id, "Geçersiz şehir. Lütfen listeden bir şehir seçin:", reply_markup=markup)
        bot.register_next_step_handler(msg, add_product_city_selected)
        return
    
    # İlçe seçim klavyesi
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Şehirlere göre ilçe listesi
    if city == "Alanya":
        ilceler = ["Merkez", "Mahmutlar", "Kestel", "Oba", "Türkler"]
    elif city == "Antalya":
        ilceler = ["Merkez", "Konyaaltı", "Muratpaşa", "Kepez"]
    else:  # İstanbul
        ilceler = ["Anadolu Yakası", "Avrupa Yakası", "Kadıköy", "Beşiktaş"]
    
    for ilce in ilceler:
        markup.add(ilce)
    markup.add("🔙 Admin Paneline Dön")
    
    msg = bot.send_message(message.chat.id, f"{city} için ilçeyi seçin:", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda m: add_product_district_selected(m, city))

def add_product_district_selected(message, city):
    if message.text == "🔙 Admin Paneline Dön":
        return admin_panel(message)
    
    district = message.text
    
    # Ürün adı için klavye
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("🔙 Admin Paneline Dön")
    
    msg = bot.send_message(
        message.chat.id, 
        f"Ürün adını girin (Örn: Ev, Daire, İş Yeri):", 
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, lambda m: add_product_name_entered(m, city, district))

def add_product_name_entered(message, city, district):
    if message.text == "🔙 Admin Paneline Dön":
        return admin_panel(message)
    
    # Ürün adını temizle - emoji veya özel karakterleri kaldır
    product_name = message.text.strip()
    # Tam ürün adını oluştur
    full_product_name = f"{city} - {district} - {product_name}"
    
    # Fiyat için klavye
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("🔙 Admin Paneline Dön")
    
    msg = bot.send_message(
        message.chat.id, 
        "Ürün fiyatını girin (sadece sayı, örn: 75):", 
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, lambda m: add_product_price_entered(m, full_product_name, city))

def add_product_price_entered(message, product_name, city):
    if message.text == "🔙 Admin Paneline Dön":
        return admin_panel(message)
    
    try:
        # Fiyat metnini temizle ve sadece sayısal değeri al
        price_text = message.text.strip()
        # Noktalama işaretlerini ve sembolleri kaldır
        price_text = ''.join(c for c in price_text if c.isdigit() or c == '.')
        price = float(price_text)
        
        # Teslimat resmi için klavye
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add("🔙 Admin Paneline Dön")
        
        msg = bot.send_message(
            message.chat.id, 
            "Teslimat resmini yükleyin (her resim 1 stok demektir):", 
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, lambda m: add_product_image_uploaded(m, product_name, price, city))
    
    except ValueError as e:
        logger.error(f"Fiyat dönüştürme hatası: {str(e)} - Girilen değer: '{message.text}'")
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add("🔙 Admin Paneline Dön")
        
        msg = bot.send_message(
            message.chat.id, 
            "Geçersiz fiyat. Lütfen sadece sayı girin (örn: 75):", 
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, lambda m: add_product_price_entered(m, product_name, city))

def add_product_image_uploaded(message, product_name, price, city):
    if message.text == "🔙 Admin Paneline Dön":
        return admin_panel(message)
    
    # Resim kontrolü
    if not message.photo:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add("🔙 Admin Paneline Dön")
        
        msg = bot.send_message(
            message.chat.id, 
            "Lütfen bir resim yükleyin:", 
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, lambda m: add_product_image_uploaded(m, product_name, price, city))
        return
    
    try:
        # En büyük boyuttaki fotoğrafı al
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Benzersiz resim ID'si oluştur
        image_id = f"img_{uuid.uuid4()}"
        image_path = os.path.join(PRODUCT_IMAGES_DIR, f"{image_id}.jpg")
        
        # Resmi kaydet
        with open(image_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        # Ürünü JSON dosyasına ekle
        product = add_product(product_name, price, city, image_id)
        
        # Başarı mesajı
        bot.send_message(
            message.chat.id, 
            f"✅ Ürün başarıyla eklendi!\n\n"
            f"Ürün: {product_name}\n"
            f"Fiyat: ${price}\n"
            f"Şehir: {city}\n"
            f"Resim ID: {image_id}"
        )
        
        # Ürün önizlemesi
        bot.send_photo(
            message.chat.id,
            open(image_path, 'rb'),
            caption=f"{product_name} - ${price}"
        )
        
        # Admin paneline dön
        admin_panel(message)
    
    except Exception as e:
        logger.error(f"Resim yükleme hatası: {str(e)}")
        bot.send_message(
            message.chat.id, 
            f"Resim yüklenirken bir hata oluştu: {str(e)}"
        )
        admin_panel(message)

@bot.message_handler(func=lambda message: message.text == '🔙 Geri Dön' or message.text == '🔙 Ana Menü' or message.text == '🔙 Geri')
def back_to_main_menu(message):
    send_welcome_message(message)

@bot.message_handler(func=lambda message: message.text == '📜 Market Kuralları')
def show_market_rules(message):
    bot.send_message(message.chat.id, f"Market kurallarımızı görmek için aşağıdaki linke tıklayın:\n{market_rules_link}")

@bot.message_handler(func=lambda message: message.text == '📰 Haber')
def show_news(message):
    bot.send_message(message.chat.id, f"Son haberlerimizi görmek için aşağıdaki linke tıklayın:\n{news_link}")

@bot.message_handler(func=lambda message: message.text == '💳 Bakiye Ekle')
def add_balance_menu(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💵 $10", "💵 $20", "💵 $50")
    markup.row("💵 $100", "💵 $200", "💵 $500")
    markup.row("🔙 Geri Dön")
    
    bot.send_message(message.chat.id, "Eklemek istediğiniz bakiye miktarını seçin:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text.startswith('💵 $'))
def handle_balance_selection(message):
    amount_str = message.text.replace('💵 $', '')
    try:
        amount = int(amount_str)
        
        # Ödeme bilgilerini göster
        payment_info = f"Bakiye eklemek için aşağıdaki TRC20 adresine ${amount} değerinde USDT gönderebilirsiniz:\n\n"
        payment_info += f"`{trc20_wallet}`\n\n"
        payment_info += "Ödeme yaptıktan sonra, işleminiz 5-10 dakika içinde onaylanacaktır."
        
        # Kullanıcının bekleyen işlemini kaydet
        user_id = message.from_user.id
        username = message.from_user.username or f"user_{user_id}"
        save_pending_transaction(user_id, amount, trc20_wallet)
        
        bot.send_message(message.chat.id, payment_info, parse_mode='Markdown')
    except ValueError:
        bot.send_message(message.chat.id, "Geçersiz miktar.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy_callback(call):
    # Callback verilerini ayır
    parts = call.data.split('_')
    if len(parts) < 3:
        bot.answer_callback_query(call.id, "Geçersiz işlem.")
        return
    
    product_id = parts[1]
    price_str = parts[2]
    
    try:
        price = float(price_str)
        
        # Ürünü kontrol et
        product = get_product_by_id(product_id)
        if not product:
            bot.answer_callback_query(call.id, "Ürün artık mevcut değil.")
            return
        
        # Kullanıcı bakiyesini kontrol et
        user_id = call.from_user.id
        username = call.from_user.username or f"user_{user_id}"
        balances = read_balances()
        user_balance = balances.get(str(user_id), {"balance": 0})["balance"]
        
        if user_balance < price:
            bot.answer_callback_query(call.id, "Yetersiz bakiye!")
            return
        
        # Bakiyeyi güncelle
        new_balance = update_balance(user_id, username, -price)
        
        # Ürünü satılanlar listesine taşı
        if move_to_sold(product_id, user_id, username):
            # Satın alma başarılı mesajı
            success_message = f"✅ Satın alma işlemi başarılı!\n\n"
            success_message += f"Ürün: {product['name']}\n"
            success_message += f"Fiyat: ${price}\n"
            success_message += f"Yeni bakiyeniz: ${new_balance}\n\n"
            success_message += "Ürün bilgileri size özel mesaj olarak gönderilecektir."
            
            bot.edit_message_text(
                success_message,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
            
            # Ürün resmini gönder
            image_id = product.get('image_id')
            if image_id:
                image_path = os.path.join(PRODUCT_IMAGES_DIR, f"{image_id}.jpg")
                if os.path.exists(image_path):
                    bot.send_photo(
                        call.message.chat.id,
                        open(image_path, 'rb'),
                        caption=f"Satın aldığınız ürün: {product['name']}"
                    )
            
            # Yorum isteme mesajı
            markup = telebot.types.InlineKeyboardMarkup()
            comment_button = telebot.types.InlineKeyboardButton(
                "Yorum Yap 💬", 
                callback_data=f"comment_{product_id}"
            )
            markup.add(comment_button)
            
            bot.send_message(
                call.message.chat.id,
                "Satın aldığınız ürün hakkında yorum yapmak ister misiniz?",
                reply_markup=markup
            )
        else:
            bot.answer_callback_query(call.id, "Satın alma işlemi başarısız oldu.")
    
    except Exception as e:
        logger.error(f"Satın alma hatası: {str(e)}")
        bot.answer_callback_query(call.id, f"Bir hata oluştu: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def handle_cancel_callback(call):
    bot.edit_message_text(
        "İşlem iptal edildi.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=None
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('comment_'))
def handle_comment_callback(call):
    product_id = call.data.split('_')[1]
    
    # Yorum için mesaj gönder
    msg = bot.send_message(
        call.message.chat.id,
        "Lütfen yorumunuzu yazın:"
    )
    
    # Bir sonraki adıma geç
    bot.register_next_step_handler(msg, lambda m: save_comment(m, product_id))

def save_comment(message, product_id):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    comment_text = message.text
    
    # Ürün bilgilerini al
    product = None
    try:
        with open(sold_file, 'r', encoding='utf-8') as f:
            sold_products = json.load(f)
            
        for p in sold_products:
            if p.get('id') == product_id:
                product = p
                break
    except:
        pass
    
    product_name = product.get('name', 'Bilinmeyen Ürün') if product else 'Bilinmeyen Ürün'
    
    # Yorumu kaydet
    try:
        with open(yorumlar_file, 'r', encoding='utf-8') as f:
            comments = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        comments = []
    
    comment_data = {
        "user_id": user_id,
        "username": username,
        "product_id": product_id,
        "product_name": product_name,
        "comment": comment_text,
        "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    comments.append(comment_data)
    
    with open(yorumlar_file, 'w', encoding='utf-8') as f:
        json.dump(comments, f, ensure_ascii=False, indent=4)
    
    # Teşekkür mesajı
    bot.send_message(
        message.chat.id,
        "Yorumunuz için teşekkür ederiz! Yorumunuz diğer kullanıcılar tarafından görülebilecektir."
    )

@bot.message_handler(func=lambda message: message.text == '👥 Kullanıcılar')
def show_users(message):
    user_id = message.from_user.id
    admins = read_admins()
    
    if user_id not in admins:
        bot.send_message(message.chat.id, "Bu özelliğe erişim izniniz yok.")
        return
    
    # Kullanıcı listesini göster
    try:
        balances = read_balances()
        
        if not balances:
            bot.send_message(message.chat.id, "Henüz hiç kullanıcı bulunmuyor.")
            return
        
        users_text = "👥 KULLANICILAR\n\n"
        for user_id, user_data in balances.items():
            username = user_data.get('username', 'Bilinmeyen')
            balance = user_data.get('balance', 0)
            users_text += f"ID: {user_id}\nKullanıcı: {username}\nBakiye: ${balance}\n\n"
        
        # Uzun mesajları bölmek için
        if len(users_text) > 4000:
            for i in range(0, len(users_text), 4000):
                bot.send_message(message.chat.id, users_text[i:i+4000])
        else:
            bot.send_message(message.chat.id, users_text)
    
    except Exception as e:
        bot.send_message(message.chat.id, f"Kullanıcılar yüklenirken bir hata oluştu: {str(e)}")

@bot.message_handler(func=lambda message: message.text == '💼 Bakiye İşlemleri')
def balance_operations(message):
    user_id = message.from_user.id
    admins = read_admins()
    
    if user_id not in admins:
        bot.send_message(message.chat.id, "Bu özelliğe erişim izniniz yok.")
        return
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Bakiye Ekle", "➖ Bakiye Çıkar")
    markup.row("🔙 Admin Paneline Dön")
    
    bot.send_message(message.chat.id, "Bakiye işlemi seçin:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["➕ Bakiye Ekle", "➖ Bakiye Çıkar"])
def handle_balance_operation(message):
    user_id = message.from_user.id
    admins = read_admins()
    
    if user_id not in admins:
        bot.send_message(message.chat.id, "Bu özelliğe erişim izniniz yok.")
        return
    
    operation = "add" if message.text == "➕ Bakiye Ekle" else "subtract"
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Admin Paneline Dön")
    
    msg = bot.send_message(
        message.chat.id, 
        "Kullanıcının ID'sini girin:", 
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, lambda m: get_balance_amount(m, operation))

def get_balance_amount(message, operation):
    if message.text == "🔙 Admin Paneline Dön":
        return admin_panel(message)
    
    try:
        target_user_id = int(message.text)
        
        # Kullanıcıyı kontrol et
        balances = read_balances()
        if str(target_user_id) not in balances:
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🔙 Admin Paneline Dön")
            
            msg = bot.send_message(
                message.chat.id, 
                "Kullanıcı bulunamadı. Lütfen geçerli bir ID girin:", 
                reply_markup=markup
            )
            bot.register_next_step_handler(msg, lambda m: get_balance_amount(m, operation))
            return
        
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔙 Admin Paneline Dön")
        
        msg = bot.send_message(
            message.chat.id, 
            f"Eklemek/çıkarmak istediğiniz bakiye miktarını girin (sadece sayı):", 
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, lambda m: process_balance_change(m, target_user_id, operation))
    
    except ValueError:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔙 Admin Paneline Dön")
        
        msg = bot.send_message(
            message.chat.id, 
            "Geçersiz ID. Lütfen sayısal bir ID girin:", 
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, lambda m: get_balance_amount(m, operation))

def process_balance_change(message, target_user_id, operation):
    if message.text == "🔙 Admin Paneline Dön":
        return admin_panel(message)
    
    try:
        amount = float(message.text)
        
        # Bakiyeyi güncelle
        balances = read_balances()
        user_data = balances.get(str(target_user_id), {})
        username = user_data.get('username', f"user_{target_user_id}")
        
        # İşleme göre bakiyeyi artır veya azalt
        if operation == "add":
            new_balance = update_balance(target_user_id, username, amount)
            operation_text = "eklendi"
        else:  # subtract
            new_balance = update_balance(target_user_id, username, -amount)
            operation_text = "çıkarıldı"
        
        bot.send_message(
            message.chat.id, 
            f"✅ İşlem başarılı!\n\n"
            f"Kullanıcı: {username}\n"
            f"ID: {target_user_id}\n"
            f"İşlem: ${amount} {operation_text}\n"
            f"Yeni bakiye: ${new_balance}"
        )
        
        # Admin paneline dön
        admin_panel(message)
    
    except ValueError:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔙 Admin Paneline Dön")
        
        msg = bot.send_message(
            message.chat.id, 
            "Geçersiz miktar. Lütfen sayısal bir değer girin:", 
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, lambda m: process_balance_change(m, target_user_id, operation))

# Start the bot
if __name__ == "__main__":
    # Create required files if they don't exist
    for file_path in [products_file, sold_file, sales_log_file, balances_file, admins_file, yorumlar_file]:
        try:
            with open(file_path, 'a+', encoding='utf-8') as f:
                if f.tell() == 0:  # Dosya boşsa
                    if file_path == products_file or file_path == sold_file or file_path == sales_log_file or file_path == yorumlar_file:
                        f.write('[]')  # Boş liste
                    elif file_path == balances_file:
                        f.write('{}')  # Boş sözlük
                    elif file_path == admins_file:
                        f.write('{"admins": []}')  # Admin listesi
        except Exception as e:
            logger.error(f"Dosya oluşturma hatası: {str(e)}")
    
    # Initialize admin file
    init_admins_file()
    
    logger.info("Bot started!")
    bot.polling(none_stop=True)

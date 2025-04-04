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
    
    # Use inline keyboard instead of reply keyboard
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    
    # City buttons
    markup.add(
        telebot.types.InlineKeyboardButton("🏙️ Alanya", callback_data="city_Alanya"),
        telebot.types.InlineKeyboardButton("🌇 Antalya", callback_data="city_Antalya"),
        telebot.types.InlineKeyboardButton("🌆 İstanbul", callback_data="city_Istanbul")
    )
    
    # Profile and comments buttons
    markup.add(
        telebot.types.InlineKeyboardButton("👤 Profil", callback_data="profile"),
        telebot.types.InlineKeyboardButton("💬 Yorumlar", callback_data="comments")
    )
    
    # Other buttons
    markup.add(
        telebot.types.InlineKeyboardButton("🏪 Vitrin", callback_data="showcase"),
        telebot.types.InlineKeyboardButton("📜 Market Kuralları", callback_data="market_rules"),
        telebot.types.InlineKeyboardButton("📰 Haber", callback_data="news")
    )
    
    # Admin panel button only for admins
    if is_admin:
        markup.add(telebot.types.InlineKeyboardButton("🔧 Admin Paneli", callback_data="admin_panel"))
    
    bot.send_message(message.chat.id, f"Merhaba! Şehir seçerek başlayabilirsiniz.\nMevcut bakiyeniz: {current_balance}$", reply_markup=markup)

# Add callback handlers for the inline buttons
@bot.callback_query_handler(func=lambda call: call.data.startswith('city_'))
def handle_city_callback(call):
    city = call.data.split('_')[1]
    if city == "Istanbul":  # Fix encoding for İstanbul
        city = "İstanbul"
    
    # Ensure we're in a private chat
    if call.message.chat.type != 'private':
        try:
            bot.send_message(call.from_user.id, "Şehir seçimi için lütfen özel sohbette devam edin.")
            return
        except:
            bot.answer_callback_query(call.id, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    # Şehre göre ürünleri göster
    products = get_products_by_city(city)
    
    # Stok durumunu kontrol et
    if not products:
        bot.answer_callback_query(call.id, f"Üzgünüz, {city} için şu anda stokta ürün bulunmuyor.")
        return
    
    # Ürünleri listele
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    for product in products:
        product_name = product.get('name')
        product_price = product.get('price')
        product_id = product.get('id')
        markup.add(telebot.types.InlineKeyboardButton(
            f"{product_name} - ${product_price} - {city}", 
            callback_data=f"product_{product_id}"
        ))
    
    markup.add(telebot.types.InlineKeyboardButton("🔙 Geri", callback_data="back_to_main"))
    
    bot.edit_message_text(
        f"{city} için mevcut ürünler:", 
        call.message.chat.id, 
        call.message.message_id, 
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('product_'))
def handle_product_callback(call):
    # Ensure we're in a private chat
    if call.message.chat.type != 'private':
        try:
            bot.send_message(call.from_user.id, "Ürün seçimi için lütfen özel sohbette devam edin.")
            return
        except:
            bot.answer_callback_query(call.id, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    # Ürün ID'sini al
    product_id = call.data.split('_')[1]
    product = get_product_by_id(product_id)
    
    if not product:
        bot.answer_callback_query(call.id, "Seçilen ürün artık mevcut değil.")
        return
    
    product_name = product.get('name')
    product_price = product.get('price')
    city = product.get('city')
    
    # Fiyatı sayıya çevir
    try:
        price = float(product_price)
    except ValueError:
        bot.answer_callback_query(call.id, "Ürün fiyatı geçersiz.")
        return
    
    # Kullanıcı bakiyesini kontrol et
    user_id = call.from_user.id
    balances = read_balances()
    user_balance = balances.get(str(user_id), {"balance": 0})["balance"]
    
    if user_balance < price:
        bot.answer_callback_query(call.id, f"Yetersiz bakiye! Bu ürün için ${price} gerekiyor. Mevcut bakiyeniz: ${user_balance}")
        return
    
    # Ürün resmini göster (varsa)
    image_id = product.get('image_id')
    if image_id:
        image_path = os.path.join(PRODUCT_IMAGES_DIR, f"{image_id}.jpg")
        if os.path.exists(image_path):
            bot.send_photo(
                call.message.chat.id,
                open(image_path, 'rb'),
                caption=f"{product_name} - ${price}"
            )
    
    # Satın alma onayı iste
    markup = telebot.types.InlineKeyboardMarkup()
    confirm_button = telebot.types.InlineKeyboardButton("Satın Al ✅", callback_data=f"buy_{product_id}_{price}")
    cancel_button = telebot.types.InlineKeyboardButton("İptal ❌", callback_data="cancel")
    markup.row(confirm_button, cancel_button)
    
    bot.send_message(
        call.message.chat.id, 
        f"Ürün: {product_name}\nFiyat: ${price}\nŞehir: {city}\nBakiyeniz: ${user_balance}\n\nSatın almak istiyor musunuz?",
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'profile')
def handle_profile_callback(call):
    # Ensure we're in a private chat
    if call.message.chat.type != 'private':
        try:
            bot.send_message(call.from_user.id, "Profil için lütfen özel sohbette devam edin.")
            return
        except:
            bot.answer_callback_query(call.id, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    user_id = call.from_user.id
    username = call.from_user.username or f"user_{user_id}"
    
    # Kullanıcı bakiyesini al
    balances = read_balances()
    user_balance = balances.get(str(user_id), {"balance": 0})["balance"]
    
    # Profil menüsünü göster
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("📦 Siparişlerim", callback_data="orders"),
        telebot.types.InlineKeyboardButton("💳 Bakiye Ekle", callback_data="add_balance")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("🌐 Site", callback_data="website"),
        telebot.types.InlineKeyboardButton("🏷️ İndirimler", callback_data="discounts")
    )
    markup.row(telebot.types.InlineKeyboardButton("🔙 Geri Dön", callback_data="back_to_main"))
    
    bot.edit_message_text(
        f"👤 Profil Bilgileri\n\nKullanıcı: {username}\nID: {user_id}\nBakiye: ${user_balance}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'orders')
def handle_orders_callback(call):
    # Ensure we're in a private chat
    if call.message.chat.type != 'private':
        try:
            bot.send_message(call.from_user.id, "Siparişlerinizi görmek için lütfen özel sohbette devam edin.")
            return
        except:
            bot.answer_callback_query(call.id, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    user_id = call.from_user.id
    username = call.from_user.username or f"user_{user_id}"
    
    # Kullanıcının siparişlerini bul
    try:
        with open(sales_log_file, 'r') as f:
            sales = json.load(f)
            
        user_orders = [sale for sale in sales if sale.get('user') == username]
        
        if not user_orders:
            bot.answer_callback_query(call.id, "Henüz hiç sipariş vermediniz.")
            return
        
        # Siparişleri listele
        orders_text = "📦 SİPARİŞLERİNİZ\n\n"
        for i, order in enumerate(user_orders, 1):
            orders_text += f"{i}. {order.get('product')} - ${order.get('price')} - {order.get('date')}\n"
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 Geri", callback_data="profile"))
        
        bot.edit_message_text(
            orders_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    except Exception as e:
        bot.answer_callback_query(call.id, f"Siparişleriniz yüklenirken bir hata oluştu: {str(e)}")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'comments')
def handle_comments_callback(call):
    # Ensure we're in a private chat
    if call.message.chat.type != 'private':
        try:
            bot.send_message(call.from_user.id, "Yorumları görmek için lütfen özel sohbette devam edin.")
            return
        except:
            bot.answer_callback_query(call.id, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    # Yorumları oku
    try:
        with open(yorumlar_file, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        
        if not comments:
            bot.answer_callback_query(call.id, "Henüz hiç yorum bulunmuyor.")
            return
        
        # Son 10 yorumu göster
        recent_comments = comments[-10:] if len(comments) > 10 else comments
        
        comments_text = "💬 MÜŞTERİ YORUMLARI\n\n"
        for comment in recent_comments:
            date = comment.get('date', '')
            product_name = comment.get('product_name', '')
            comment_text = comment.get('comment', '')
            comments_text += f"📅 {date}\n🏷️ {product_name}\n💭 {comment_text}\n\n"
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 Geri", callback_data="back_to_main"))
        
        bot.edit_message_text(
            comments_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    except FileNotFoundError:
        bot.answer_callback_query(call.id, "Henüz hiç yorum bulunmuyor.")
    except Exception as e:
        bot.answer_callback_query(call.id, f"Yorumlar yüklenirken bir hata oluştu: {str(e)}")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_panel')
def handle_admin_panel_callback(call):
    # Ensure we're in a private chat
    if call.message.chat.type != 'private':
        try:
            bot.send_message(call.from_user.id, "Admin paneli için lütfen özel sohbette devam edin.")
            return
        except:
            bot.answer_callback_query(call.id, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    user_id = call.from_user.id
    admins = read_admins()
    
    if user_id not in admins:
        bot.answer_callback_query(call.id, "Bu özelliğe erişim izniniz yok.")
        return
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton("📊 Satış Raporu", callback_data="sales_report"),
        telebot.types.InlineKeyboardButton("📦 Stok Durumu", callback_data="stock_status")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("👥 Kullanıcılar", callback_data="users"),
        telebot.types.InlineKeyboardButton("💼 Bakiye İşlemleri", callback_data="balance_operations")
    )
    markup.add(telebot.types.InlineKeyboardButton("➕ Ürün Ekle", callback_data="add_product"))
    markup.add(telebot.types.InlineKeyboardButton("🔙 Ana Menü", callback_data="back_to_main"))
    
    bot.edit_message_text(
        "Admin Paneli'ne Hoş Geldiniz",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'market_rules')
def handle_market_rules_callback(call):
    bot.answer_callback_query(call.id, f"Market kurallarımızı görmek için: {market_rules_link}")

@bot.callback_query_handler(func=lambda call: call.data == 'news')
def handle_news_callback(call):
    bot.answer_callback_query(call.id, f"Son haberlerimizi görmek için: {news_link}")

@bot.callback_query_handler(func=lambda call: call.data == 'add_balance')
def handle_add_balance_callback(call):
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        telebot.types.InlineKeyboardButton("💵 $10", callback_data="balance_10"),
        telebot.types.InlineKeyboardButton("💵 $20", callback_data="balance_20"),
        telebot.types.InlineKeyboardButton("💵 $50", callback_data="balance_50")
    )
    markup.add(
        telebot.types.InlineKeyboardButton("💵 $100", callback_data="balance_100"),
        telebot.types.InlineKeyboardButton("💵 $200", callback_data="balance_200"),
        telebot.types.InlineKeyboardButton("💵 $500", callback_data="balance_500")
    )
    markup.add(telebot.types.InlineKeyboardButton("🔙 Geri", callback_data="profile"))
    
    bot.edit_message_text(
        "Eklemek istediğiniz bakiye miktarını seçin:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('balance_'))
def handle_balance_amount_callback(call):
    amount_str = call.data.split('_')[1]
    try:
        amount = int(amount_str)
        
        # Ödeme bilgilerini göster
        payment_info = f"Bakiye eklemek için aşağıdaki TRC20 adresine ${amount} değerinde USDT gönderebilirsiniz:\n\n"
        payment_info += f"`{trc20_wallet}`\n\n"
        payment_info += "Ödeme yaptıktan sonra, işleminiz 5-10 dakika içinde onaylanacaktır."
        
        # Kullanıcının bekleyen işlemini kaydet
        user_id = call.from_user.id
        username = call.from_user.username or f"user_{user_id}"
        save_pending_transaction(user_id, amount, trc20_wallet)
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 Geri", callback_data="add_balance"))
        
        bot.edit_message_text(
            payment_info,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except ValueError:
        bot.answer_callback_query(call.id, "Geçersiz miktar.")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def handle_back_to_main_callback(call):
    # Return to main menu
    user_id = call.from_user.id
    username = call.from_user.username or f"user_{user_id}"
    
    # Initialize user with 0 balance if not exists
    current_balance = update_balance(user_id, username)
    
    # Check if user is admin
    admins = read_admins()
    is_admin = user_id in admins
    
    # Use inline keyboard
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    
    # City buttons
    markup.add(
        telebot.types.InlineKeyboardButton("🏙️ Alanya", callback_data="city_Alanya"),
        telebot.types.InlineKeyboardButton("🌇 Antalya", callback_data="city_Antalya"),
        telebot.types.InlineKeyboardButton("🌆 İstanbul", callback_data="city_Istanbul")
    )
    
    # Profile and comments buttons
    markup.add(
        telebot.types.InlineKeyboardButton("👤 Profil", callback_data="profile"),
        telebot.types.InlineKeyboardButton("💬 Yorumlar", callback_data="comments")
    )
    
    # Other buttons
    markup.add(
        telebot.types.InlineKeyboardButton("🏪 Vitrin", callback_data="showcase"),
        telebot.types.InlineKeyboardButton("📜 Market Kuralları", callback_data="market_rules"),
        telebot.types.InlineKeyboardButton("📰 Haber", callback_data="news")
    )
    
    # Admin panel button only for admins
    if is_admin:
        markup.add(telebot.types.InlineKeyboardButton("🔧 Admin Paneli", callback_data="admin_panel"))
    
    bot.edit_message_text(
        f"Merhaba! Şehir seçerek başlayabilirsiniz.\nMevcut bakiyeniz: {current_balance}$",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

# Add more callback handlers for other buttons as needed
@bot.callback_query_handler(func=lambda call: call.data == 'sales_report')
def handle_sales_report_callback(call):
    user_id = call.from_user.id
    admins = read_admins()
    
    if user_id not in admins:
        bot.answer_callback_query(call.id, "Bu özelliğe erişim izniniz yok.")
        return
    
    # Satış raporunu oluştur
    try:
        with open(sales_log_file, 'r') as f:
            sales = json.load(f)
            
        if not sales:
            bot.answer_callback_query(call.id, "Henüz satış kaydı bulunmuyor.")
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
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 Admin Paneline Dön", callback_data="admin_panel"))
        
        bot.edit_message_text(
            report,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    except Exception as e:
        bot.answer_callback_query(call.id, f"Satış raporu oluşturulurken bir hata oluştu: {str(e)}")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy_callback(call):
    # Ensure we're in a private chat
    if call.message.chat.type != 'private':
        try:
            bot.send_message(call.from_user.id, "Satın alma işlemi için lütfen özel sohbette devam edin.")
            return
        except:
            bot.answer_callback_query(call.id, "Lütfen önce botla özel sohbet başlatın.")
            return
    
    # Ürün ID'sini ve fiyatını al
    parts = call.data.split('_')
    product_id = parts[1]
    price = float(parts[2])
    
    # Kullanıcı bilgilerini al
    user_id = call.from_user.id
    username = call.from_user.username or f"user_{user_id}"
    
    # Kullanıcı bakiyesini kontrol et
    balances = read_balances()
    user_balance = balances.get(str(user_id), {"balance": 0})["balance"]
    
    if user_balance < price:
        bot.answer_callback_query(call.id, "Yetersiz bakiye! Lütfen bakiye ekleyin.")
        return
    
    # Ürünü kontrol et
    product = get_product_by_id(product_id)
    if not product:
        bot.answer_callback_query(call.id, "Ürün artık mevcut değil.")
        return
    
    # Bakiyeyi güncelle
    new_balance = update_balance(user_id, username, -price)
    
    # Ürünü satılanlar listesine taşı
    success = move_to_sold(product_id, user_id, username)
    
    if success:
        # Başarılı satın alma mesajı
        bot.send_message(
            call.message.chat.id,
            f"✅ Satın alma işlemi başarılı!\n\n"
            f"Ürün: {product['name']}\n"
            f"Fiyat: ${price}\n"
            f"Yeni bakiyeniz: ${new_balance}\n\n"
            f"Ürün detayları size özel mesaj olarak gönderilecektir."
        )
        
        # Ürün detaylarını özel mesaj olarak gönder
        bot.send_message(
            call.message.chat.id,
            f"🔐 ÜRÜN BİLGİLERİ 🔐\n\n"
            f"Ürün: {product['name']}\n"
            f"Şehir: {product['city']}\n\n"
            f"Satın aldığınız için teşekkür ederiz!"
        )
        
        # Admin'e bildirim gönder
        admins = read_admins()
        for admin_id in admins:
            try:
                bot.send_message(
                    admin_id,
                    f"💰 YENİ SATIŞ 💰\n\n"
                    f"Kullanıcı: {username}\n"
                    f"Ürün: {product['name']}\n"
                    f"Fiyat: ${price}\n"
                    f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception as e:
                logger.error(f"Admin bildirim hatası: {str(e)}")
    else:
        # Başarısız satın alma durumunda bakiyeyi geri ver
        update_balance(user_id, username, price)
        bot.send_message(
            call.message.chat.id,
            "❌ Satın alma işlemi başarısız oldu. Lütfen daha sonra tekrar deneyin."
        )
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def handle_cancel_callback(call):
    bot.edit_message_text(
        "İşlem iptal edildi.",
        call.message.chat.id,
        call.message.message_id
    )
    
    # Ana menüye dönmek için buton ekle
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🔙 Ana Menü", callback_data="back_to_main"))
    
    bot.send_message(
        call.message.chat.id,
        "Ana menüye dönmek için tıklayın:",
        reply_markup=markup
    )
    
    bot.answer_callback_query(call.id)

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

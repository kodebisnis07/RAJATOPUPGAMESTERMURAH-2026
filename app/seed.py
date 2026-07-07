import json
from app.extensions import db
from app.models import Admin, Category, CatalogSection, Product, Setting, Banner, Promo, Testimonial, FAQ, Voucher
from app.utils import unique_slug

SEED_GAMES = [
    {"name": "Mobile Legends", "products": [("86 Diamonds", 20000), ("172 Diamonds", 39000), ("257 Diamonds", 58000)]},
    {"name": "PUBG Mobile", "products": [("60 UC", 15000), ("325 UC", 75000), ("660 UC", 145000)]},
    {"name": "Free Fire", "products": [("70 Diamonds", 10000), ("140 Diamonds", 20000), ("355 Diamonds", 50000)]},
    {"name": "Valorant", "products": [("125 Points", 15000), ("420 Points", 50000), ("700 Points", 80000)]},
    {"name": "Genshin Impact", "products": [("60 Genesis Crystals", 16000), ("300 Genesis Crystals", 79000), ("980 Genesis Crystals", 249000)]},
    {"name": "Steam Wallet", "products": [("Steam Wallet Rp45.000", 45000), ("Steam Wallet Rp60.000", 60000), ("Steam Wallet Rp90.000", 90000)]},
]

DEFAULT_SETTINGS = {
    "payment_gateway": "manual",
    "tripay_mode": "sandbox",
    "site_name": "RAJA TOPUP GAMES",
    "site_tagline": "Top Up Game Termurah, Cepat, Aman, dan Terpercaya",
    "whatsapp": "",
    "telegram": "",
    "instagram": "",
}


RAJATOPUP_EXTRA_CATALOG = [

    {
        "section": {"title": "Top Up Games", "slug": "top-up-games", "subtitle": "Pilihan game lengkap: terlaris, populer, dan game lainnya.", "sort_order": 1},
        "categories": [
            {"name": "Magic Chess: Go Go", "badge": "TERLARIS", "icon": "game-magic-chess-go-go.png", "products": [("Paket Top Up Magic Chess", 10000)]},
            {"name": "PUBG Mobile", "badge": "TERLARIS", "icon": "game-pubg-mobile.png", "products": [("60 UC", 15000), ("325 UC", 75000), ("660 UC", 145000)]},
            {"name": "Honor of Kings Global", "badge": "TERLARIS", "icon": "game-honor-of-kings-global.png", "products": [("Tokens Honor of Kings", 10000)]},
            {"name": "Genshin Impact", "badge": "TERLARIS", "icon": "game-genshin-impact.png", "products": [("60 Genesis Crystals", 16000), ("300 Genesis Crystals", 79000), ("980 Genesis Crystals", 249000)]},
            {"name": "Arena Breakout", "badge": "TERLARIS", "icon": "game-arena-breakout.png", "products": [("Bonds Arena Breakout", 10000)]},
            {"name": "Valorant", "badge": "TERLARIS", "icon": "game-valorant.png", "products": [("125 Points", 15000), ("420 Points", 50000), ("700 Points", 80000)]},
            {"name": "Blood Strike", "badge": "POPULER", "icon": "game-blood-strike.png", "products": [("Gold Blood Strike", 10000)]},
            {"name": "Roblox", "badge": "POPULER", "icon": "game-roblox.png", "products": [("Robux Roblox", 10000)]},
            {"name": "8 Ball Pool", "badge": "POPULER", "icon": "game-8-ball-pool.png", "products": [("Cash/Coin 8 Ball Pool", 10000)]},
            {"name": "Growtopia", "badge": "POPULER", "icon": "game-growtopia.png", "products": [("World Lock Growtopia", 10000)]},
            {"name": "State of Survival", "badge": "POPULER", "icon": "game-state-of-survival.png", "products": [("Biocaps State of Survival", 10000)]},
            {"name": "Whiteout Survival", "badge": "POPULER", "icon": "game-whiteout-survival.png", "products": [("Frost Star Whiteout Survival", 10000)]},
            {"name": "Dragon Nest 2: Evolution", "badge": "GAME", "icon": "game-dragon-nest-2-evolution.png", "products": [("Paket Top Up Dragon Nest 2", 10000)]},
            {"name": "Dragonheir: Silent Gods", "badge": "GAME", "icon": "game-dragonheir-silent-gods.png", "products": [("Paket Top Up Dragonheir", 10000)]},
            {"name": "Fisch (Roblox)", "badge": "GAME", "icon": "game-fisch-roblox.png", "products": [("Paket Fisch Roblox", 10000)]},
            {"name": "Dragon Raja", "badge": "GAME", "icon": "game-dragon-raja.png", "products": [("Coupon Dragon Raja", 10000)]},
            {"name": "Sausage Man", "badge": "GAME", "icon": "game-sausage-man.png", "products": [("Candy Sausage Man", 10000)]},
            {"name": "Mobile Legends", "badge": "GAME", "icon": "game-mobile-legends.png", "products": [("86 Diamonds", 20000), ("172 Diamonds", 39000), ("257 Diamonds", 58000)]},
            {"name": "Free Fire", "badge": "GAME", "icon": "game-free-fire.png", "products": [("70 Diamonds", 10000), ("140 Diamonds", 20000), ("355 Diamonds", 50000)]},
            {"name": "Clash of Clans", "badge": "GAME", "icon": "game-clash-of-clans.png", "products": [("Gold Pass Clash of Clans", 10000)]},
            {"name": "Love and Deepspace", "badge": "GAME", "icon": "game-love-and-deepspace.png", "products": [("Crystal Love and Deepspace", 10000)]},
            {"name": "Garena Shell", "badge": "GAME", "icon": "game-garena-shell.png", "products": [("Garena Shell", 10000)]},
            {"name": "Honkai Star Rail", "badge": "GAME", "icon": "game-honkai-star-rail.png", "products": [("Oneiric Shard", 10000)]},
            {"name": "Metal Slug: Awakening", "badge": "GAME", "icon": "game-metal-slug-awakening.png", "products": [("Ruby Metal Slug", 10000)]},
            {"name": "League of Legends: Wild Rift", "badge": "GAME", "icon": "game-league-of-legends-wild-rift.png", "products": [("Wild Core", 10000)]},
            {"name": "Eggy Party", "badge": "GAME", "icon": "game-eggy-party.png", "products": [("Egg Coin", 10000)]},
            {"name": "Super Sus", "badge": "GAME", "icon": "game-super-sus.png", "products": [("Gold Star Super Sus", 10000)]},
            {"name": "Hago", "badge": "GAME", "icon": "game-hago.png", "products": [("Diamond Hago", 10000)]},
            {"name": "Point Blank", "badge": "GAME", "icon": "game-point-blank.png", "products": [("PB Cash", 10000)]},
            {"name": "EA SPORTS FC Mobile", "badge": "GAME", "icon": "game-ea-sports-fc-mobile.png", "products": [("FC Points", 10000)]},
            {"name": "Lords Mobile", "badge": "GAME", "icon": "game-lords-mobile.png", "products": [("Diamonds Lords Mobile", 10000)]},
            {"name": "Steam Wallet", "badge": "GAME", "icon": "game-steam-wallet.png", "products": [("Steam Wallet Rp45.000", 45000), ("Steam Wallet Rp60.000", 60000), ("Steam Wallet Rp90.000", 90000)]},
            {"name": "League of Legends: PC", "badge": "GAME", "icon": "game-league-of-legends-pc.png", "products": [("RP League of Legends PC", 10000)]},
            {"name": "Ace Racer", "badge": "GAME", "icon": "game-ace-racer.png", "products": [("Ace Racer Token", 10000)]},
            {"name": "Tower Of Fantasy", "badge": "GAME", "icon": "game-tower-of-fantasy.png", "products": [("Tanium Tower of Fantasy", 10000)]},
            {"name": "LifeAfter", "badge": "GAME", "icon": "game-lifeafter.png", "products": [("Credits LifeAfter", 10000)]},
            {"name": "Ragnarok M", "badge": "GAME", "icon": "game-ragnarok-m.png", "products": [("Big Cat Coin", 10000)]},
            {"name": "Ragnarok Origin", "badge": "GAME", "icon": "game-ragnarok-origin.png", "products": [("Nyan Berry", 10000)]},
            {"name": "Garena Undawn", "badge": "GAME", "icon": "game-garena-undawn.png", "products": [("RC Undawn", 10000)]},
            {"name": "Omega Legends", "badge": "GAME", "icon": "game-omega-legends.png", "products": [("Gold Omega Legends", 10000)]},
            {"name": "Arena of Valor", "badge": "GAME", "icon": "game-arena-of-valor.png", "products": [("Voucher AOV", 10000)]},
            {"name": "Revelation", "badge": "GAME", "icon": "game-revelation.png", "products": [("Paket Top Up Revelation", 10000)]},
            {"name": "Hyper Front", "badge": "GAME", "icon": "game-hyper-front.png", "products": [("Star Quartz Hyper Front", 10000)]},
            {"name": "MARVEL Super War", "badge": "GAME", "icon": "game-marvel-super-war.png", "products": [("Star Credit MARVEL Super War", 10000)]},
            {"name": "Tom and Jerry: Chase", "badge": "GAME", "icon": "game-tom-and-jerry-chase.png", "products": [("Diamond Tom and Jerry", 10000)]},
            {"name": "One Punch Man", "badge": "GAME", "icon": "game-one-punch-man.png", "products": [("Voucher One Punch Man", 10000)]},
            {"name": "Light of Thel", "badge": "GAME", "icon": "game-light-of-thel.png", "products": [("Crystal Light of Thel", 10000)]},
        ],
    },
    {
        "section": {"title": "Aplikasi Premium", "slug": "aplikasi-premium", "subtitle": "Voucher app premium lengkap: Netflix, YouTube, Canva, AI tools, streaming, musik, dan aplikasi lainnya.", "sort_order": 2},
        "categories": [
            {"name": "Netflix Premium", "badge": "APP", "icon": "app-netflix-premium.png", "products": [("Netflix Premium 1 Bulan", 65000)]},
            {"name": "YouTube Premium", "badge": "APP", "icon": "app-youtube-premium.png", "products": [("YouTube Premium 1 Bulan", 55000)]},
            {"name": "CapCut Pro", "badge": "APP", "icon": "app-capcut-pro.png", "products": [("CapCut Pro 1 Bulan", 75000)]},
            {"name": "Canva Pro", "badge": "APP", "icon": "app-canva-pro.png", "products": [("Canva Pro 1 Bulan", 25000)]},
            {"name": "ChatGPT", "badge": "AI", "icon": "app-chatgpt.png", "products": [("ChatGPT 1 Bulan", 95000)]},
            {"name": "Video Premier", "badge": "APP", "icon": "app-video-premier.png", "products": [("Video Premier", 0)]},
            {"name": "WeTV Premium", "badge": "APP", "icon": "app-wetv-premium.png", "products": [("WeTV Premium 1 Bulan", 35000)]},
            {"name": "SuperGrok", "badge": "AI", "icon": "app-supergrok.png", "products": [("SuperGrok Premium", 0)]},
            {"name": "Viu Premium", "badge": "APP", "icon": "app-viu-premium.png", "products": [("Viu Premium", 0)]},
            {"name": "Bstation Premium", "badge": "APP", "icon": "app-bstation-premium.png", "products": [("Bstation Premium", 0)]},
            {"name": "Disney Hotstar", "badge": "APP", "icon": "app-disney-hotstar.png", "products": [("Disney Hotstar 1 Bulan", 65000)]},
            {"name": "Gemini", "badge": "AI", "icon": "app-gemini.png", "products": [("Gemini Pro 3 Bulan", 75000)]},
            {"name": "iQIYI", "badge": "APP", "icon": "app-iqiyi.png", "products": [("iQIYI 1 Bulan", 65000)]},
            {"name": "Akun Gmail", "badge": "APP", "icon": "app-akun-gmail.png", "products": [("Akun Gmail", 0)]},
            {"name": "Vision Plus", "badge": "APP", "icon": "app-vision-plus.png", "products": [("Vision Plus", 0)]},
            {"name": "Spotify Murah", "badge": "APP", "icon": "app-spotify-murah.png", "products": [("Spotify Premium", 0)]},
            {"name": "Amazon Prime Video", "badge": "APP", "icon": "app-amazon-prime-video.png", "products": [("Amazon Prime Video", 0)]},
            {"name": "Perplexity", "badge": "AI", "icon": "app-perplexity.png", "products": [("Perplexity Pro", 0)]},
            {"name": "Webtoon", "badge": "APP", "icon": "app-webtoon.png", "products": [("Webtoon", 0)]},
            {"name": "Getcontact Premium", "badge": "APP", "icon": "app-getcontact-premium.png", "products": [("Getcontact Premium", 0)]},
            {"name": "Google Play", "badge": "APP", "icon": "app-google-play.png", "products": [("Voucher Google Play", 0)]},
            {"name": "Alight Motion", "badge": "APP", "icon": "app-alight-motion.png", "products": [("Alight Motion Premium", 0)]},
            {"name": "Website Topup Games", "badge": "JASA", "icon": "app-website-topup-games.png", "products": [("Pembuatan Website Topup Games", 0)]},
        ],
    },
    {
        "section": {"title": "Voucher", "slug": "voucher", "subtitle": "Voucher game dan digital populer.", "sort_order": 3},
        "categories": [
            {"name": "Google Play Voucher", "badge": "VOUCHER", "icon": "app-google-play.png", "products": [("Google Play Rp20.000", 22000), ("Google Play Rp50.000", 53000), ("Google Play Rp100.000", 105000)]},
            {"name": "Steam Wallet Voucher", "badge": "VOUCHER", "icon": "game-steam-wallet.png", "products": [("Steam Wallet Rp45.000", 48000), ("Steam Wallet Rp60.000", 63000), ("Steam Wallet Rp90.000", 94000)]},
            {"name": "Garena Shell Voucher", "badge": "VOUCHER", "icon": "game-garena-shell.png", "products": [("33 Shell", 10000), ("66 Shell", 20000), ("165 Shell", 50000)]},
            {"name": "Roblox Gift Card", "badge": "VOUCHER", "icon": "game-roblox.png", "products": [("Roblox Gift Card Rp50.000", 55000), ("Roblox Gift Card Rp100.000", 105000)]},
        ],
    },
    {
        "section": {"title": "Pulsa", "slug": "pulsa", "subtitle": "Pulsa semua operator.", "sort_order": 4},
        "categories": [
            {"name": "Pulsa Telkomsel", "badge": "PULSA", "products": [("Telkomsel 5.000", 6500), ("Telkomsel 10.000", 11500), ("Telkomsel 20.000", 21500), ("Telkomsel 50.000", 51000)]},
            {"name": "Pulsa XL", "badge": "PULSA", "products": [("XL 5.000", 6500), ("XL 10.000", 11500), ("XL 20.000", 21500), ("XL 50.000", 51000)]},
            {"name": "Pulsa Axis", "badge": "PULSA", "products": [("Axis 5.000", 6500), ("Axis 10.000", 11500), ("Axis 20.000", 21500), ("Axis 50.000", 51000)]},
            {"name": "Pulsa Indosat", "badge": "PULSA", "products": [("Indosat 5.000", 6500), ("Indosat 10.000", 11500), ("Indosat 20.000", 21500), ("Indosat 50.000", 51000)]},
            {"name": "Pulsa Tri", "badge": "PULSA", "products": [("Tri 5.000", 6500), ("Tri 10.000", 11500), ("Tri 20.000", 21500), ("Tri 50.000", 51000)]},
            {"name": "Pulsa Smartfren", "badge": "PULSA", "products": [("Smartfren 5.000", 6500), ("Smartfren 10.000", 11500), ("Smartfren 20.000", 21500), ("Smartfren 50.000", 51000)]},
        ],
    },
    {
        "section": {"title": "E-Wallet", "slug": "e-wallet", "subtitle": "Top up saldo e-wallet Indonesia.", "sort_order": 5},
        "categories": [
            {"name": "DANA", "badge": "EWALLET", "products": [("DANA 20.000", 22000), ("DANA 50.000", 52000), ("DANA 100.000", 102000)]},
            {"name": "OVO", "badge": "EWALLET", "products": [("OVO 20.000", 22000), ("OVO 50.000", 52000), ("OVO 100.000", 102000)]},
            {"name": "GoPay", "badge": "EWALLET", "products": [("GoPay 20.000", 22000), ("GoPay 50.000", 52000), ("GoPay 100.000", 102000)]},
            {"name": "ShopeePay", "badge": "EWALLET", "products": [("ShopeePay 20.000", 22000), ("ShopeePay 50.000", 52000), ("ShopeePay 100.000", 102000)]},
            {"name": "LinkAja", "badge": "EWALLET", "products": [("LinkAja 20.000", 22000), ("LinkAja 50.000", 52000), ("LinkAja 100.000", 102000)]},
        ],
    },
    {
        "section": {"title": "Suntik Sosmed", "slug": "suntik-sosmed", "subtitle": "Reseller sosmed terlengkap: followers, likes, views, subscribers, members, traffic, dan engagement.", "sort_order": 3},
        "categories": [
            {"name": "Favorite Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/favorite.png", "products": [("Paket Rekomendasi Sosmed", 10000), ("Paket Terlaris Sosmed", 25000), ("Paket Campuran Sosmed", 50000)]},
            {"name": "Facebook Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1779699774_191d079998cbab8a767e.webp", "products": [("1K Facebook Followers", 30000), ("3K Facebook Followers", 65000), ("5K Facebook Followers", 95000), ("1K Facebook Likes", 30000), ("1K Facebook Views", 20000)]},
            {"name": "Instagram Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778744356_471d397c44e29664fa93.webp", "products": [("1K Instagram Followers", 85000), ("3K Instagram Followers", 185000), ("5K Instagram Followers", 255000), ("1K Instagram Likes", 35000), ("3K Instagram Likes", 65000), ("5K Instagram Likes", 85000)]},
            {"name": "TikTok Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778744454_d98c8a5f695fa9fe2e31.webp", "products": [("1K TikTok Followers", 95000), ("2K TikTok Followers", 180000), ("3K TikTok Followers", 250000), ("1K TikTok Likes", 25000), ("3K TikTok Likes", 45000), ("5K TikTok Likes", 85000), ("10K TikTok Views", 30000)]},
            {"name": "Promo Sosmed", "badge": "PROMO", "icon": "https://rajaitem.com/assets/images/layanan/1778744836_5da79e7173455f3c7b6a.webp", "products": [("Promo Followers", 10000), ("Promo Likes", 10000), ("Promo Views", 10000)]},
            {"name": "Binance Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778744888_bbdf540d278c1c444dbf.webp", "products": [("Binance Engagement", 10000), ("Binance Traffic", 25000)]},
            {"name": "GitHub Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778744943_fa202e623c9714a426ff.webp", "products": [("GitHub Stars", 10000), ("GitHub Followers", 15000), ("GitHub Forks", 20000)]},
            {"name": "Kick Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778744992_233342b5994d8949cd03.webp", "products": [("Kick Followers", 15000), ("Kick Views", 20000)]},
            {"name": "Bigo Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778745035_301ad19ffbe7831630d6.webp", "products": [("Bigo Followers", 15000), ("Bigo Views", 20000)]},
            {"name": "CapCut Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778745083_a0a3e6a31bae6cabfbc2.webp", "products": [("CapCut Followers", 15000), ("CapCut Likes", 15000), ("CapCut Views", 20000)]},
            {"name": "WhatsApp Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778745135_978792316619d42f0b99.webp", "products": [("WhatsApp Channel Followers", 20000), ("WhatsApp Group Member", 25000)]},
            {"name": "Google Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778745179_7715a3e4b85fb7cac80c.webp", "products": [("Google Review", 25000), ("Google Maps Rating", 25000)]},
            {"name": "Twitter / X Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778745252_1554c3daabf4485b0f26.webp", "products": [("Twitter/X Followers", 15000), ("Twitter/X Likes", 15000), ("Twitter/X Retweet", 15000)]},
            {"name": "YouTube Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778745288_1b79d02a9025821a36a5.webp", "products": [("YouTube Subscribers", 20000), ("YouTube Likes", 15000), ("YouTube Views", 20000), ("YouTube Watch Hours", 50000)]},
            {"name": "Telegram Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778745321_ccc8d47fc055ac075ee8.webp", "products": [("1K Telegram Followers", 65000), ("3K Telegram Followers", 135000), ("5K Telegram Followers", 215000), ("Telegram Channel Member", 20000), ("Telegram Post Views", 15000)]},
            {"name": "Threads Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778745354_7743a900fcf95edc0fe3.webp", "products": [("Threads Followers", 15000), ("Threads Likes", 15000)]},
            {"name": "Traffic Website", "badge": "TRAFFIC", "icon": "https://rajaitem.com/assets/images/layanan/1778745390_1504440404b5fe8dd2d6.webp", "products": [("Traffic Website Indonesia", 25000), ("Traffic Website Global", 30000), ("SEO Traffic", 50000)]},
            {"name": "Discord Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778745424_617e6acb9bb722b10db3.webp", "products": [("Discord Member", 20000), ("Discord Online Member", 30000)]},
            {"name": "LinkedIn Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778745455_23c195a87752b0f0b6d7.webp", "products": [("LinkedIn Followers", 20000), ("LinkedIn Likes", 15000), ("LinkedIn Connections", 25000)]},
            {"name": "Spotify Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778745491_98089b9ac1c493b95102.webp", "products": [("Spotify Plays", 15000), ("Spotify Followers", 20000), ("Spotify Saves", 15000)]},
            {"name": "Shopee Sosmed", "badge": "SOSMED", "icon": "https://rajaitem.com/assets/images/layanan/1778745526_8ecca0ee5ce26097f7ca.webp", "products": [("Shopee Followers", 15000), ("Shopee Likes", 15000), ("Shopee Product Views", 20000)]},
        ],
    },
    {
        "section": {"title": "Telegram Premium", "slug": "telegram-premium", "subtitle": "Aktivasi Telegram Premium 3 bulan, 6 bulan, dan 1 tahun.", "sort_order": 4},
        "categories": [
            {"name": "Telegram Premium", "badge": "TG", "products": [("Telegram Premium 3 Bulan", 260000), ("Telegram Premium 6 Bulan", 360000), ("Telegram Premium 1 Tahun", 560000)]},
        ],
    },
    {
        "section": {"title": "Telegram Stars", "slug": "telegram-stars", "subtitle": "Top up Telegram Stars mulai dari 50 sampai 1000 Stars.", "sort_order": 5},
        "categories": [
            {"name": "Telegram Stars", "badge": "STARS", "products": [("50 Stars", 18000), ("75 Stars", 23000), ("100 Stars", 35000), ("150 Stars", 50000), ("200 Stars", 70000), ("250 Stars", 80000), ("300 Stars", 95000), ("350 Stars", 105000), ("400 Stars", 120000), ("500 Stars", 145000), ("1000 Stars", 290000)]},
        ],
    },
]



def seed_raja_extra_catalog():
    changed = False
    for group in RAJATOPUP_EXTRA_CATALOG:
        sec_data = group["section"]
        section = CatalogSection.query.filter_by(slug=sec_data["slug"]).first()
        if not section:
            section = CatalogSection(
                title=sec_data["title"],
                slug=sec_data["slug"],
                subtitle=sec_data.get("subtitle"),
                sort_order=sec_data.get("sort_order", 0),
                is_active=True,
            )
            db.session.add(section)
            db.session.flush()
            changed = True
        else:
            section.title = sec_data["title"]
            section.subtitle = sec_data.get("subtitle")
            section.sort_order = sec_data.get("sort_order", section.sort_order or 0)
            section.is_active = True
            changed = True

        for idx, cat_data in enumerate(group["categories"], start=1):
            cat_slug = unique_slug(Category, cat_data["name"])
            category = Category.query.filter_by(name=cat_data["name"]).first()
            if not category:
                category = Category(
                    name=cat_data["name"],
                    slug=cat_slug,
                    status="active",
                    catalog_section_id=section.id,
                    sort_order=idx,
                    is_featured=True,
                    badge=cat_data.get("badge"),
                    icon=cat_data.get("icon"),
                )
                db.session.add(category)
                db.session.flush()
                changed = True
            else:
                category.catalog_section_id = section.id
                category.status = "active"
                category.is_featured = True
                category.badge = cat_data.get("badge")
                category.icon = cat_data.get("icon") or category.icon
                if not category.sort_order:
                    category.sort_order = idx
                changed = True

            for product_name, price in cat_data["products"]:
                product = Product.query.filter_by(category_id=category.id, name=product_name).first()
                if not product:
                    product = Product(
                        category_id=category.id,
                        name=product_name,
                        slug=unique_slug(Product, f"{category.name} {product_name}"),
                        description=f"Layanan {product_name} untuk {category.name}.",
                        price_modal=0,
                        price=price,
                        stock=999,
                        status="active",
                    )
                    db.session.add(product)
                    changed = True
                else:
                    product.price = price
                    product.stock = product.stock or 999
                    product.status = "active"
                    changed = True

    if changed:
        db.session.commit()


def seed_initial_data():
    changed = False

    for key, value in DEFAULT_SETTINGS.items():
        if not Setting.query.filter_by(key=key).first():
            db.session.add(Setting(key=key, value=value))
            changed = True

    admin = Admin.query.filter_by(username="admin").first()
    if not admin:
        admin = Admin(username="admin", name="Super Admin", role="super_admin", is_active=True)
        admin.set_password("Admin@123")
        db.session.add(admin)
        changed = True
    else:
        # Pastikan akun utama selalu memiliki akses penuh.
        admin.name = admin.name or "Super Admin"
        admin.role = "super_admin"
        admin.is_active = True
        changed = True

    default_section = CatalogSection.query.filter_by(slug="game-populer").first()
    if not default_section:
        default_section = CatalogSection(
            title="Game Populer",
            slug="game-populer",
            subtitle="Pilih game, lalu lanjutkan ke halaman top up.",
            sort_order=1,
            is_active=True,
        )
        db.session.add(default_section)
        db.session.flush()
        changed = True

    if Category.query.count() == 0:
        for index, item in enumerate(SEED_GAMES, start=1):
            category = Category(name=item["name"], slug=unique_slug(Category, item["name"]), status="active", catalog_section_id=default_section.id, sort_order=index, is_featured=True)
            db.session.add(category)
            db.session.flush()
            for product_name, price in item["products"]:
                product = Product(
                    category_id=category.id,
                    name=product_name,
                    slug=unique_slug(Product, f"{item['name']} {product_name}"),
                    description=f"Top up {product_name} untuk {item['name']}.",
                    price_modal=0,
                    price=price,
                    stock=999,
                    status="active",
                )
                db.session.add(product)
        changed = True

    if default_section and Category.query.filter(Category.catalog_section_id.is_(None)).count():
        Category.query.filter(Category.catalog_section_id.is_(None)).update({"catalog_section_id": default_section.id})
        changed = True

    # Banner utama/hero website. Bagian ini sengaja ikut memperbaiki database lama
    # yang masih berisi banner default tanpa gambar, supaya setelah deploy tampilan
    # langsung berubah tanpa perlu hapus data manual dari admin panel.
    default_hero_image = "img/banner/rtg-banner-20260707.png"
    existing_banners = Banner.query.order_by(Banner.sort_order.asc(), Banner.id.asc()).all()
    default_titles = {"Promo Mobile Legends", "RAJA TOPUP GAMES", "Pembayaran Mudah", "TOPUP GAMES", "TOP UP GAMES"}
    if not existing_banners:
        banners = [
            Banner(title="TOPUP GAMES", tag="RAJA TOPUP GAMES", subtitle="TERMURAH & TERPERCAYA!", button_text="Top Up Sekarang", link="#games", sort_order=1, is_active=True, image=default_hero_image),
        ]
        db.session.add_all(banners)
        changed = True
    elif all((b.title in default_titles or not b.image) for b in existing_banners[:4]):
        main = existing_banners[0]
        main.title = "TOPUP GAMES"
        main.tag = "RAJA TOPUP GAMES"
        main.subtitle = "TERMURAH & TERPERCAYA!"
        main.button_text = "Top Up Sekarang"
        main.link = "#games"
        main.sort_order = 1
        main.is_active = True
        main.image = default_hero_image
        for extra in existing_banners[1:]:
            extra.is_active = False
        changed = True

    if not Setting.query.filter_by(key="website_banners_json").first():
        website_banners = [
            {"id":"default-reseller","title":"Gabung Reseller Raja Topup","subtitle":"Dapatkan harga khusus reseller dan kelola pelanggan lebih mudah.","badge":"RESELLER","button_text":"Daftar Reseller","link":"/reseller","sort_order":1,"is_active":True,"image":None},
            {"id":"default-promo","title":"Promo & Voucher Aktif","subtitle":"Cek voucher dan promo terbaru sebelum checkout agar transaksi makin hemat.","badge":"PROMO WEBSITE","button_text":"Lihat Promo","link":"#promo","sort_order":2,"is_active":True,"image":None},
        ]
        db.session.add(Setting(key="website_banners_json", value=json.dumps(website_banners, ensure_ascii=False)))
        changed = True

    if Voucher.query.count() == 0:
        db.session.add_all([
            Voucher(code="RAJA10", title="Diskon Member Baru", discount_type="percent", discount_value=10, min_order=10000, quota=100, is_active=True),
            Voucher(code="HEMAT5K", title="Potongan Rp5.000", discount_type="fixed", discount_value=5000, min_order=50000, quota=0, is_active=True),
        ])
        changed = True

    if Promo.query.count() == 0:
        db.session.add_all([
            Promo(title="Promo Member Baru", description="Dapatkan harga spesial untuk transaksi pertama Anda.", badge="BARU", link="#games"),
            Promo(title="Flash Sale Mingguan", description="Pantau promo game populer setiap minggu di RAJA TOPUP GAMES.", badge="FLASH"),
            Promo(title="Top Up Cepat", description="Pesanan diproses cepat dengan sistem yang terus dikembangkan.", badge="CEPAT"),
        ])
        changed = True

    if Testimonial.query.count() == 0:
        db.session.add_all([
            Testimonial(name="Andi", message="Tampilannya bagus dan proses top up mudah dipahami.", rating=5),
            Testimonial(name="Rizky", message="Harga jelas, menu rapi, cocok untuk kebutuhan top up game.", rating=5),
            Testimonial(name="Salsa", message="Dashboard adminnya makin lengkap dan mudah digunakan.", rating=5),
        ])
        changed = True

    if FAQ.query.count() == 0:
        db.session.add_all([
            FAQ(question="Bagaimana cara top up?", answer="Pilih game, pilih nominal, isi data akun game, lalu lanjutkan ke pembayaran.", sort_order=1),
            FAQ(question="Apakah pembayaran otomatis?", answer="Saat ini sistem disiapkan untuk payment gateway. Setelah Tripay aktif, status pembayaran bisa otomatis.", sort_order=2),
            FAQ(question="Apakah bisa tambah game sendiri?", answer="Bisa. Admin dapat menambah kategori dan produk melalui dashboard.", sort_order=3),
        ])
        changed = True

    if changed:
        db.session.commit()

    seed_raja_extra_catalog()

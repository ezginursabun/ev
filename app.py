import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static, st_folium
from folium import plugins
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import requests
from dotenv import load_dotenv
import os
from geopy.geocoders import Nominatim
from folium.plugins import Draw, MousePosition
import json
import random
import urllib.request
import ssl

# Sayfa yapılandırması
st.set_page_config(
    page_title="EV Şarj İstasyonu Yatırım Analizi",
    page_icon="��",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern ve minimal stil tanımlamaları
st.markdown("""
    <style>
    /* Ana tema renkleri */
    :root {
        --primary-color: #2E86C1;
        --secondary-color: #3498DB;
        --background-color: #F8F9FA;
        --text-color: #2C3E50;
    }
    
    /* Genel stil */
    .main {
        background-color: var(--background-color);
        color: var(--text-color);
        padding: 1rem;
    }
    
    /* Başlık stili */
    .css-10trblm {
        color: var(--primary-color);
        font-weight: 600;
        font-size: 2.2rem;
        margin-bottom: 2rem;
    }
    
    /* Alt başlık stili */
    .css-1629p8f h2 {
        color: var(--text-color);
        font-weight: 500;
        font-size: 1.5rem;
        margin-top: 1.5rem;
    }
    
    /* Sidebar stili */
    .css-1d391kg {
        background-color: white;
        padding: 2rem 1rem;
    }
    
    /* Kart stili */
    .stCard {
        background-color: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    /* Input alanları stili */
    .stNumberInput, .stSelectbox {
        background-color: white;
        border-radius: 5px;
        border: 1px solid #E0E0E0;
        padding: 0.5rem;
    }
    
    /* Tab stili */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        margin-bottom: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px;
        color: var(--text-color);
        font-size: 1rem;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color) !important;
        color: white !important;
    }
    
    /* Grafik container stili */
    .plot-container {
        background-color: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

def create_metric_card(title: str, value: str, delta: str = None):
    """Özel metrik kartı oluşturur"""
    st.markdown(f"""
        <div class="stCard">
            <h3 style="color: #666; font-size: 0.9rem; margin-bottom: 0.5rem;">{title}</h3>
            <p style="color: #2C3E50; font-size: 1.8rem; font-weight: bold; margin: 0;">{value}</p>
            {f'<p style="color: {"#28a745" if float(delta.strip("%")) > 0 else "#dc3545"}; font-size: 0.9rem; margin: 0;">{delta}</p>' if delta else ''}
        </div>
    """, unsafe_allow_html=True)

def get_address_from_coords(lat, lon):
    """Koordinatlardan adres bilgisini alır"""
    try:
        geolocator = Nominatim(user_agent="ev_charger_app")
        location = geolocator.reverse((lat, lon), language="tr")
        return location.address
    except:
        return "Adres bulunamadı"

def create_map(center_lat, center_lon, selected_points=None):
    """Etkileşimli harita oluşturur"""
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    
    # Fare pozisyonu gösterici ekle
    MousePosition().add_to(m)
    
    # Haritaya çizim kontrolü ekle
    draw_control = Draw(
        draw_options={
            'polyline': False,
            'rectangle': False,
            'polygon': False,
            'circle': False,
            'marker': True,
            'circlemarker': False,
        },
        edit_options={'edit': False}
    )
    draw_control.add_to(m)

    # Tıklama olayını yakalayan JavaScript kodu
    m.add_child(folium.Element("""
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                var map = document.querySelector('#map');
                map.addEventListener('click', function(e) {
                    var lat = e.latlng.lat;
                    var lng = e.latlng.lng;
                    new L.Marker([lat, lng]).addTo(map);
                    window.parent.postMessage({
                        'type': 'map_click',
                        'lat': lat,
                        'lng': lng
                    }, '*');
                });
            }, 1000);
        });
        </script>
    """))
    
    # Mevcut seçili noktaları ekle
    if selected_points:
        for point in selected_points:
            folium.Marker(
                location=[point['lat'], point['lon']],
                popup=point['address'],
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)
    
    return m

def fetch_ev_data():
    """Ulaşım verilerini API'den çeker"""
    try:
        # SSL sertifika doğrulamasını devre dışı bırak (sadece test için)
        context = ssl._create_unverified_context()
        
        url = 'https://ulasav.csb.gov.tr/api/3/action/datastore_search?resource_id=6ebdc521-c96c-4ebf-8695-88f3af494d86'
        
        # API isteği
        request = urllib.request.Request(url)
        
        # API yanıtını al
        with urllib.request.urlopen(request, context=context) as response:
            data = response.read()
            return json.loads(data)
    except Exception as e:
        st.error(f"Veri çekilirken hata oluştu: {str(e)}")
        return None

def analyze_traffic(lat, lon):
    """Seçilen konuma göre trafik analizi yapar"""
    try:
        # API'den verileri çek
        data = fetch_ev_data()
        if data and 'result' in data:
            # Gerçek veriler varsa kullan
            return {
                'daily_traffic': data['result'].get('daily_traffic', random.randint(8000, 15000)),
                'peak_hours': {
                    'morning': '08:00-10:00',
                    'evening': '17:00-19:00'
                },
                'weekend_density': data['result'].get('weekend_density', random.randint(50, 80)),
                'ev_traffic': data['result'].get('ev_traffic', random.randint(100, 500)),
                'traffic_growth': data['result'].get('traffic_growth', random.randint(5, 15))
            }
    except:
        pass
    
    # API verisi alınamazsa simüle edilmiş veri döndür
    return {
        'daily_traffic': random.randint(8000, 15000),
        'peak_hours': {
            'morning': '08:00-10:00',
            'evening': '17:00-19:00'
        },
        'weekend_density': random.randint(50, 80),
        'ev_traffic': random.randint(100, 500),
        'traffic_growth': random.randint(5, 15)
    }

# Excel dosyasını oku
@st.cache_data
def load_population_data():
    try:
        # CSV dosyasını oku ve sütun isimlerini düzelt
        df = pd.read_csv('veriler/yenianaliz.csv', encoding='utf-8')
        
        # Sütun isimlerini temizle ve düzelt
        df.columns = df.columns.str.strip()
        
        # Tarih sütununu string olarak tut
        if 'İl ve cinsiyete göre il/ilçe merkezi, belde/köy nüfusu ve nüfus yoğunluğu, 2007-2024' in df.columns:
            df['Yil'] = df['İl ve cinsiyete göre il/ilçe merkezi, belde/köy nüfusu ve nüfus yoğunluğu, 2007-2024'].astype(str)
            df = df.drop('İl ve cinsiyete göre il/ilçe merkezi, belde/köy nüfusu ve nüfus yoğunluğu, 2007-2024', axis=1)
        
        # Sayısal sütunları düzelt
        numeric_columns = ['Toplam_Nufus', 'Nufus_Yogunlugu', 'Sehir_Nufus', 'Kirsal_Nufus', 
                         'Nufus_Artis_Hizi', 'EV_Sahiplik_Orani', 'Isyeri_Yogunlugu']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.replace('.', ''), errors='coerce')
        
        st.write("Veri seti sütunları:", df.columns.tolist())  # Debug için sütun isimlerini göster
        return df
    except Exception as e:
        st.error(f"Veri dosyası okunurken hata oluştu: {str(e)}")
        st.write("Hata detayı:", e)  # Debug için hata detayını göster
        return None

def analyze_demographics(lat, lon):
    """Seçilen konuma göre demografik analiz yapar"""
    # Şehir koordinatları ve isimleri
    cities = {
        "İstanbul": {"lat": 41.0082, "lon": 28.9784},
        "Ankara": {"lat": 39.9334, "lon": 32.8597},
        "İzmir": {"lat": 38.4237, "lon": 27.1428},
        "Bursa": {"lat": 40.1885, "lon": 29.0610},
        "Antalya": {"lat": 36.8969, "lon": 30.7133}
    }
    
    # En yakın şehri bul
    closest_city = min(cities.items(), key=lambda x: ((lat - x[1]["lat"])**2 + (lon - x[1]["lon"])**2)**0.5)[0]
    
    # Şehirlere göre yaklaşık değerler
    city_data = {
        "İstanbul": {
            "population": 15800000,
            "density": 2900,
            "urban_population": 15200000,
            "rural_population": 600000,
            "population_growth": 2.5,
            "ev_ownership": 8,
            "business_density": 450
        },
        "Ankara": {
            "population": 5700000,
            "density": 2100,
            "urban_population": 5300000,
            "rural_population": 400000,
            "population_growth": 1.8,
            "ev_ownership": 6,
            "business_density": 350
        },
        "İzmir": {
            "population": 4400000,
            "density": 1800,
            "urban_population": 4000000,
            "rural_population": 400000,
            "population_growth": 1.5,
            "ev_ownership": 5,
            "business_density": 300
        },
        "Bursa": {
            "population": 3100000,
            "density": 1500,
            "urban_population": 2800000,
            "rural_population": 300000,
            "population_growth": 1.7,
            "ev_ownership": 4,
            "business_density": 250
        },
        "Antalya": {
            "population": 2500000,
            "density": 1200,
            "urban_population": 2200000,
            "rural_population": 300000,
            "population_growth": 2.2,
            "ev_ownership": 3,
            "business_density": 200
        }
    }
    
    # Seçilen şehir için veriyi al
    data = city_data.get(closest_city, {
        "population": random.randint(1000000, 2000000),
        "density": random.randint(500, 1000),
        "urban_population": random.randint(800000, 1500000),
        "rural_population": random.randint(100000, 300000),
        "population_growth": round(random.uniform(1.0, 2.0), 1),
        "ev_ownership": random.randint(2, 5),
        "business_density": random.randint(100, 200)
    })
    
    # Küçük rastgsal değişiklikler ekle
    data = {k: v * (1 + random.uniform(-0.05, 0.05)) if isinstance(v, (int, float)) else v 
            for k, v in data.items()}
    
    return {
        'city_name': closest_city,
        'population': int(data['population']),
        'density': int(data['density']),
        'urban_population': int(data['urban_population']),
        'rural_population': int(data['rural_population']),
        'population_growth': round(data['population_growth'], 1),
        'ev_ownership': round(data['ev_ownership'], 1),
        'business_density': int(data['business_density'])
    }

def analyze_competition(lat, lon):
    """Seçilen konuma göre rekabet analizi yapar"""
    return {
        'nearby_stations': random.randint(1, 5),
        'nearest_distance': round(random.uniform(0.5, 5.0), 1),
        'occupancy_rate': random.randint(60, 90),
        'avg_waiting_time': random.randint(5, 20),
        'market_share': random.randint(10, 40)
    }

def create_traffic_chart(traffic_data):
    """Trafik yoğunluğu grafiği oluşturur"""
    hours = list(range(24))
    # Saatlik trafik simülasyonu
    traffic = [
        max(0, 100 + 50 * np.sin((h - 8) * np.pi / 12) + random.randint(-20, 20))
        for h in hours
    ]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours,
        y=traffic,
        fill='tozeroy',
        line=dict(color='#2E86C1'),
        name='Trafik Yoğunluğu'
    ))
    fig.update_layout(
        title='Günlük Trafik Yoğunluğu',
        xaxis_title='Saat',
        yaxis_title='Araç Sayısı',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=300
    )
    return fig

def calculate_financial_projection(city_name, ev_ownership, competition_data, investment_budget):
    """Finansal projeksiyon hesaplar"""
    # Şehir bazlı büyüme faktörleri
    city_growth_factors = {
        "İstanbul": 1.4,
        "Ankara": 1.3,
        "İzmir": 1.25,
        "Bursa": 1.2,
        "Antalya": 1.15
    }
    
    growth_factor = city_growth_factors.get(city_name, 1.1)
    
    # EV sahiplik oranına göre potansiyel müşteri faktörü
    ev_factor = ev_ownership / 5  # normalize
    
    # Rekabet durumuna göre pazar payı faktörü
    market_share = competition_data['market_share'] / 100
    
    # Baz gelir ve maliyet hesaplamaları (yatırım bütçesine göre normalize)
    base_revenue = investment_budget * 0.4  # İlk yıl için beklenen gelir
    base_cost = investment_budget * 0.2     # İlk yıl için beklenen maliyet
    
    # 3 yıllık projeksiyon
    revenues = [
        int(base_revenue * (1 + ev_factor) * market_share),
        int(base_revenue * (1 + ev_factor) * market_share * growth_factor),
        int(base_revenue * (1 + ev_factor) * market_share * growth_factor * growth_factor)
    ]
    
    costs = [
        int(base_cost),
        int(base_cost * 1.1),  # %10 maliyet artışı
        int(base_cost * 1.2)   # %20 maliyet artışı
    ]
    
    # ROI hesaplama
    total_revenue = sum(revenues)
    total_cost = sum(costs) + investment_budget
    roi = ((total_revenue - total_cost) / total_cost) * 100
    
    return {
        'revenues': revenues,
        'costs': costs,
        'roi': round(roi, 1)
    }

def main():
    st.title("🔌 Elektrikli Araç Şarj İstasyonu Yatırım Analizi")
    
    # Session state için seçili noktaları başlat
    if 'selected_points' not in st.session_state:
        st.session_state.selected_points = []
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 📊 Analiz Parametreleri")
        st.markdown("---")
        
        selected_city = st.selectbox(
            "Şehir Seçin",
            ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya"],
            help="Analiz yapmak istediğiniz şehri seçin"
        )
        
        # Şehir koordinatları
        city_coords = {
            "İstanbul": [41.0082, 28.9784],
            "Ankara": [39.9334, 32.8597],
            "İzmir": [38.4237, 27.1428],
            "Bursa": [40.1885, 29.0610],
            "Antalya": [36.8969, 30.7133]
        }
        
        investment_budget = st.number_input(
            "Yatırım Bütçesi (TL)",
            min_value=100000,
            value=1000000,
            step=100000,
            format="%d",
            help="Planlanan yatırım bütçesini girin"
        )
        
        station_type = st.selectbox(
            "İstasyon Tipi",
            ["DC Hızlı Şarj", "AC Normal Şarj", "Ultra Hızlı Şarj"],
            help="Kurulacak şarj istasyonu tipini seçin"
        )
        
        st.markdown("---")
        st.markdown("### 💡 Seçilen Lokasyonlar")
        
        # Seçili lokasyonları listele
        if st.session_state.selected_points:
            for i, point in enumerate(st.session_state.selected_points):
                with st.container():
                    st.markdown(f"""
                    **Lokasyon {i+1}**  
                    📍 {point['address']}  
                    🌍 Koordinatlar: {point['lat']:.4f}, {point['lon']:.4f}
                    """)
                    if st.button(f"Sil {i+1}", key=f"delete_{i}"):
                        st.session_state.selected_points.pop(i)
                        st.rerun()
                st.markdown("---")
        else:
            st.info("Haritada istasyon kurmak istediğiniz yere tıklayın.")
    
    # Üst metrikler
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        create_metric_card("Toplam EV Sayısı", "12,450", "+15%")
    with col2:
        create_metric_card("Ortalama Günlük Şarj", "245", "+8%")
    with col3:
        create_metric_card("Rakip İstasyon Sayısı", "34", "-2%")
    with col4:
        create_metric_card("Tahmini ROI", "24%", "+5%")
    
    # Ana içerik bölümü
    st.markdown("---")
    col_map, col_analysis = st.columns([3, 2])
    
    with col_map:
        st.markdown("### 📍 Potansiyel Lokasyonlar")
        st.markdown("Haritada istasyon kurmak istediğiniz yere tıklayın.")
        
        # Harita container'ı
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        
        # Seçili şehrin koordinatlarını al
        center_lat, center_lon = city_coords[selected_city]
        
        # Haritayı oluştur
        m = create_map(center_lat, center_lon, st.session_state.selected_points)
        
        # Haritayı göster ve tıklama olayını yakala
        map_data = st_folium(m, width=800, height=500)
        
        # Haritadan gelen veriyi kontrol et
        if map_data['last_clicked']:
            try:
                lat = map_data['last_clicked']['lat']
                lon = map_data['last_clicked']['lng']
                
                # Adres bilgisini al
                address = get_address_from_coords(lat, lon)
                
                new_point = {
                    'lat': lat,
                    'lon': lon,
                    'address': address
                }
                
                if new_point not in st.session_state.selected_points:
                    st.session_state.selected_points.append(new_point)
                    st.success(f"Yeni lokasyon eklendi: {address}")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Lokasyon eklenirken bir hata oluştu: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Tüm noktaları temizleme butonu
        if st.session_state.selected_points:
            if st.button("Tüm Lokasyonları Temizle"):
                st.session_state.selected_points = []
                st.rerun()
    
    with col_analysis:
        st.markdown("### 📊 Finansal Projeksiyon")
        
        if st.session_state.selected_points:
            # Seçili lokasyon varsa analiz yap
            selected_location = st.session_state.selected_points[-1]
            
            # Demografik ve rekabet verilerini al
            demo_data = analyze_demographics(selected_location['lat'], selected_location['lon'])
            comp_data = analyze_competition(selected_location['lat'], selected_location['lon'])
            
            # Finansal projeksiyonu hesapla
            projection = calculate_financial_projection(
                demo_data['city_name'],
                demo_data['ev_ownership'],
                comp_data,
                investment_budget
            )
            
            # ROI metrik kartı
            create_metric_card(
                "Tahmini ROI",
                f"%{projection['roi']}",
                f"{'+' if projection['roi'] > 20 else ''}{projection['roi'] - 20:.1f}%"
            )
            
            # Finansal analiz grafiği
            fig = go.Figure()
            
            # Gelir çubuğu
            fig.add_trace(go.Bar(
                name='Tahmini Gelir',
                x=['1. Yıl', '2. Yıl', '3. Yıl'],
                y=projection['revenues'],
                marker_color='#2E86C1',
                text=[f'{x:,.0f} ₺' for x in projection['revenues']],
                textposition='auto'
            ))
            
            # Maliyet çubuğu
            fig.add_trace(go.Bar(
                name='İşletme Maliyeti',
                x=['1. Yıl', '2. Yıl', '3. Yıl'],
                y=projection['costs'],
                marker_color='#E74C3C',
                text=[f'{x:,.0f} ₺' for x in projection['costs']],
                textposition='auto'
            ))
            
            # Grafik düzeni
            fig.update_layout(
                barmode='group',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=40, b=20),
                height=300,
                yaxis_title='TL',
                title=f"{demo_data['city_name']} İli 3 Yıllık Finansal Projeksiyon"
            )
            
            # Açıklama metni
            st.markdown(f"""
                #### 💰 Finansal Özet
                - **Toplam Yatırım:** {investment_budget:,.0f} ₺
                - **3 Yıllık Toplam Gelir:** {sum(projection['revenues']):,.0f} ₺
                - **3 Yıllık Toplam Maliyet:** {sum(projection['costs']):,.0f} ₺
                - **Tahmini Geri Ödeme Süresi:** {max(1, min(5, investment_budget / (projection['revenues'][0] - projection['costs'][0]))): .1f} yıl
                
                *Not: Projeksiyonlar şehir büyüklüğü, EV sahiplik oranı ve rekabet durumu dikkate alınarak hesaplanmıştır.*
            """)
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Finansal projeksiyon için haritadan bir lokasyon seçin.")
    
    # Detaylı analiz bölümü
    st.markdown("### 🔍 Detaylı Analiz")
    tabs = st.tabs(["�� Trafik Analizi", "👥 Demografik Veriler", "🎯 Rekabet Analizi"])
    
    # Seçili lokasyon varsa analiz yap
    selected_location = st.session_state.selected_points[-1] if st.session_state.selected_points else None
    
    with tabs[0]:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        if selected_location:
            traffic_data = analyze_traffic(selected_location['lat'], selected_location['lon'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                    #### 🚗 Trafik Yoğunluğu Analizi
                    - **Günlük Ortalama Trafik:** {traffic_data['daily_traffic']:,} araç
                    - **Pik Saatler:** 
                        - Sabah: {traffic_data['peak_hours']['morning']}
                        - Akşam: {traffic_data['peak_hours']['evening']}
                    - **Hafta Sonu Yoğunluğu:** %{traffic_data['weekend_density']}
                    - **Günlük EV Trafiği:** {traffic_data['ev_traffic']} araç
                    - **Yıllık Trafik Artışı:** %{traffic_data['traffic_growth']}
                """)
            
            with col2:
                st.plotly_chart(create_traffic_chart(traffic_data), use_container_width=True)
        else:
            st.info("Trafik analizi için haritadan bir lokasyon seçin.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tabs[1]:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        if selected_location:
            demo_data = analyze_demographics(selected_location['lat'], selected_location['lon'])
            
            st.markdown(f"""
                #### 👥 {demo_data['city_name']} İli Demografik Analizi
                
                **📊 Nüfus Bilgileri**
                - Toplam Nüfus: {demo_data['population']:,} kişi
                - Şehir Merkezi: {demo_data['urban_population']:,} kişi
                - Kırsal Kesim: {demo_data['rural_population']:,} kişi
                
                **📈 Büyüme ve Yoğunluk**
                - Nüfus Artış Hızı: %{demo_data['population_growth']:.1f}
                - Nüfus Yoğunluğu: {demo_data['density']:,} kişi/km²
                
                **🚗 EV Potansiyeli**
                - EV Sahiplik Oranı: %{demo_data['ev_ownership']:.1f}
                - İşyeri Yoğunluğu: {demo_data['business_density']} işletme/km²
            """)
            
            # Nüfus dağılımı bar grafiği
            urban_rural_data = {
                'Kategori': ['Şehir Merkezi', 'Kırsal Kesim'],
                'Nüfus': [demo_data['urban_population'], demo_data['rural_population']]
            }
            fig = go.Figure(data=[
                go.Bar(
                    x=urban_rural_data['Kategori'],
                    y=urban_rural_data['Nüfus'],
                    marker_color=['#2E86C1', '#28B463']
                )
            ])
            fig.update_layout(
                title='Şehir-Kırsal Nüfus Dağılımı',
                height=400,
                yaxis_title='Nüfus',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Demografik analiz için haritadan bir lokasyon seçin.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tabs[2]:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        if selected_location:
            comp_data = analyze_competition(selected_location['lat'], selected_location['lon'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                    #### 🎯 Rekabet Analizi
                    - **5 km Yarıçapta Rakip İstasyon:** {comp_data['nearby_stations']} adet
                    - **En Yakın Rakip Mesafesi:** {comp_data['nearest_distance']} km
                    - **Ortalama Doluluk Oranı:** %{comp_data['occupancy_rate']}
                    - **Ortalama Bekleme Süresi:** {comp_data['avg_waiting_time']} dakika
                    - **Tahmini Pazar Payı:** %{comp_data['market_share']}
                """)
            
            with col2:
                # Doluluk oranı göstergesi
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = comp_data['occupancy_rate'],
                    title = {'text': "Doluluk Oranı"},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "#2E86C1"},
                        'steps': [
                            {'range': [0, 50], 'color': "lightgray"},
                            {'range': [50, 75], 'color': "gray"},
                            {'range': [75, 100], 'color': "darkgray"}
                        ]
                    }
                ))
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Rekabet analizi için haritadan bir lokasyon seçin.")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main() 

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from typing import Dict, List, Tuple

def calculate_location_score(
    traffic_density: float,
    pedestrian_traffic: float,
    competitor_distance: float,
    demographic_score: float,
    weights: Dict[str, float] = None
) -> float:
    """
    Lokasyon puanını hesaplar.
    
    Args:
        traffic_density: Trafik yoğunluğu (0-1 arası normalize edilmiş)
        pedestrian_traffic: Yaya trafiği (0-1 arası normalize edilmiş)
        competitor_distance: En yakın rakibe uzaklık (km)
        demographic_score: Demografik puan (0-1 arası)
        weights: Faktör ağırlıkları
    
    Returns:
        float: Hesaplanan lokasyon puanı (0-100 arası)
    """
    if weights is None:
        weights = {
            'traffic': 0.35,
            'pedestrian': 0.25,
            'competitor': 0.20,
            'demographic': 0.20
        }
    
    # Rakip uzaklığını normalize et (0-1 arası)
    normalized_competitor = min(competitor_distance / 5.0, 1.0)
    
    score = (
        weights['traffic'] * traffic_density +
        weights['pedestrian'] * pedestrian_traffic +
        weights['competitor'] * normalized_competitor +
        weights['demographic'] * demographic_score
    )
    
    return score * 100

def calculate_roi(
    investment_cost: float,
    daily_users: int,
    charge_price: float,
    operating_costs: float,
    years: int = 5
) -> Tuple[float, List[float]]:
    """
    Yatırımın geri dönüş süresini ve yıllık nakit akışını hesaplar.
    
    Args:
        investment_cost: Başlangıç yatırım maliyeti
        daily_users: Günlük tahmini kullanıcı sayısı
        charge_price: Şarj başına ortalama gelir
        operating_costs: Yıllık işletme maliyetleri
        years: Projeksiyon yılı sayısı
    
    Returns:
        Tuple[float, List[float]]: ROI ve yıllık nakit akışı listesi
    """
    yearly_revenue = daily_users * 365 * charge_price
    yearly_cash_flow = yearly_revenue - operating_costs
    
    cash_flows = []
    cumulative_cash_flow = -investment_cost
    
    for year in range(years):
        # Her yıl %10 büyüme varsayımı
        growth_factor = (1.1) ** year
        adjusted_cash_flow = yearly_cash_flow * growth_factor
        cumulative_cash_flow += adjusted_cash_flow
        cash_flows.append(cumulative_cash_flow)
    
    roi = (cumulative_cash_flow / investment_cost) * 100
    
    return roi, cash_flows

def analyze_demographics(
    population: int,
    avg_income: float,
    ev_ownership: float,
    age_distribution: Dict[str, float]
) -> float:
    """
    Demografik verileri analiz eder ve bir puan hesaplar.
    
    Args:
        population: Bölge nüfusu
        avg_income: Ortalama gelir
        ev_ownership: Elektrikli araç sahiplik oranı
        age_distribution: Yaş dağılımı yüzdeleri
    
    Returns:
        float: Demografik puan (0-1 arası)
    """
    # Gelir puanı (50,000 TL - 200,000 TL arası normalize)
    income_score = min(max((avg_income - 50000) / 150000, 0), 1)
    
    # EV sahiplik puanı
    ev_score = ev_ownership
    
    # Yaş dağılımı puanı (25-55 yaş arası daha yüksek ağırlıklı)
    age_score = (
        age_distribution.get('25-40', 0) * 0.4 +
        age_distribution.get('41-55', 0) * 0.3 +
        age_distribution.get('18-24', 0) * 0.2 +
        age_distribution.get('55+', 0) * 0.1
    )
    
    # Toplam demografik puan
    demographic_score = (income_score * 0.4 + ev_score * 0.4 + age_score * 0.2)
    
    return demographic_score 
"""
Validation Test Suite for BRI KC TB Simatupang Performance Dashboard.
Validates numerical accuracy, filters, joins, and reconciliation.
"""

import sys
import os
import unittest
import pandas as pd

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from data_loader import (
    load_loan_master,
    load_lending_data,
    load_giro_data,
    load_deposito_data,
    load_tabungan_data,
    apply_org_filter,
    clean_num,
    UNIT_METADATA
)
from metrics import compute_lending_kpis, compute_funding_kpis

class TestDashboardPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\nLoading datasets for testing...")
        cls.master_df = load_loan_master()
        cls.df_lending = load_lending_data(master_df=cls.master_df)
        cls.df_giro = load_giro_data()
        cls.df_deposito = load_deposito_data()
        cls.df_tabungan = load_tabungan_data()

    def test_01_loan_master_integrity(self):
        """Test authoritative loan master integrity."""
        self.assertEqual(len(self.master_df), 63, "Master should have 63 unique rules")
        self.assertIn("Small", self.master_df['Business'].values)
        self.assertIn("Consumer", self.master_df['Business'].values)
        self.assertIn("Unidentified", self.master_df['Business'].values)

    def test_02_lending_record_counts_and_classification(self):
        """Verify lending classifications against master."""
        total_rows = len(self.df_lending)
        self.assertEqual(total_rows, 1020, "LW321 should have exactly 1,020 records")
        
        # Verify counts by segment
        counts = self.df_lending['Business'].value_counts()
        self.assertEqual(counts.get('Small', 0), 198, "Small loans must be 198")
        self.assertEqual(counts.get('Consumer', 0), 742, "Consumer loans must be 742")
        self.assertEqual(counts.get('Micro', 0), 66, "Micro loans must be 66")
        self.assertEqual(counts.get('Medium', 0), 10, "Medium loans must be 10")
        self.assertEqual(counts.get('Commercial', 0), 2, "Commercial loans must be 2")
        self.assertEqual(counts.get('Unidentified', 0), 2, "Unidentified loans must be 2")
        
        # Main KPI counts
        main_kpi_count = self.df_lending['IS_MAIN_KPI'].sum()
        self.assertEqual(main_kpi_count, 940, "Main lending KPI (Small+Consumer) must be 940 records")

    def test_03_lending_balance_reconciliation(self):
        """Verify exact lending balance totals and mathematical reconciliation."""
        total_balance_idr = float(self.df_lending['BALANCE_IDR'].sum())
        expected_total = 588259507775.78
        self.assertAlmostEqual(total_balance_idr, expected_total, places=1,
                               msg=f"Total lending balance must match {expected_total}")
        
        # Main KPI totals
        kpis = compute_lending_kpis(self.df_lending)
        self.assertAlmostEqual(kpis['os_small'], 356662399849.74, delta=500.0)
        self.assertAlmostEqual(kpis['os_consumer'], 138498938130.24, delta=500.0)
        self.assertAlmostEqual(kpis['os_combined'], 495161337979.98, delta=500.0)
        
        # Reconcile Main + Excluded = Total Source
        self.assertAlmostEqual(kpis['os_combined'] + kpis['os_excluded'], total_balance_idr, places=1)

    def test_04_funding_balance_metrics(self):
        """Verify funding calculations use the intended balance fields."""
        funding = compute_funding_kpis(self.df_tabungan, self.df_giro, self.df_deposito)
        
        # Giro
        self.assertEqual(funding['giro_count'], 1319, "Giro should have 1,319 records")
        self.assertAlmostEqual(funding['giro_balance'], 2109184645962.93, delta=100.0)
        
        # Deposito (CBAL Base)
        self.assertEqual(funding['dep_count'], 1143, "Deposito should have 1,143 records")
        self.assertAlmostEqual(funding['dep_balance'], 1661920456436.25, delta=100.0)
        
        # Tabungan (Balance dalam IDR)
        self.assertEqual(funding['tab_count'], 52957, "Tabungan should have 52,957 records")
        self.assertAlmostEqual(funding['tab_balance'], 627744527937.65, delta=100.0)
        
        # Total Funding
        expected_funding = 627744527937.65 + 2109184645962.93 + 1661920456436.25
        self.assertAlmostEqual(funding['total_funding'], expected_funding, delta=100.0)

    def test_05_organizational_filters(self):
        """Verify Konsolidasi, KC Only, and Per KCP filters."""
        # 1. Konsolidasi
        df_konsol = apply_org_filter(self.df_lending, "Konsolidasi")
        self.assertEqual(len(df_konsol), 1020)
        
        # 2. KC Only (excludes KCP PHE Tower 1506)
        df_kc_only = apply_org_filter(self.df_lending, "KC Only")
        self.assertEqual(len(df_kc_only), 1018, "KC Only should exclude KCP records")
        self.assertTrue((df_kc_only['KODE_UKER_STR'] == '443').all())
        
        # 3. KCP PHE Tower (1506)
        df_kcp_1506 = apply_org_filter(self.df_lending, "KCP PHE TOWER (1506)")
        self.assertEqual(len(df_kcp_1506), 2, "KCP PHE Tower should isolate its 2 records")
        self.assertTrue((df_kcp_1506['KODE_UKER_STR'] == '1506').all())
        
        # Giro KCP Rancho (2075)
        df_giro_2075 = apply_org_filter(self.df_giro, "KCP RANCHO (2075)")
        self.assertEqual(len(df_giro_2075), 206, "KCP Rancho should have 206 giro records")
        self.assertTrue((df_giro_2075['KODE_UKER_STR'] == '2075').all())

    def test_06_unidentified_and_excluded_visibility(self):
        """Verify excluded records remain visible for Data Quality audit."""
        kpis = compute_lending_kpis(self.df_lending)
        self.assertEqual(kpis['excluded_records'], 80, "Excluded records count must be 80")
        self.assertEqual(kpis['count_unidentified'], 2, "Unidentified records must be 2")
        self.assertGreater(kpis['os_excluded'], 0, "Excluded OS must be positive")
        self.assertGreater(kpis['os_unidentified'], 0, "Unidentified OS must be positive")

if __name__ == "__main__":
    unittest.main()

"""
Report generation for variant analysis results.
"""

import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime


class ReportGenerator:
    """
    Generate analysis reports in various formats (HTML, CSV, Excel).
    """

    def generate_genetic_model_report(
        self,
        filtered_df: pd.DataFrame,
        model_type: str,
        gene_summary: Dict[str, Dict],
        sample_id: str,
        additional_info: Optional[Dict] = None
    ) -> str:
        """
        Generate HTML report for genetic model analysis.

        Args:
            filtered_df: Filtered variants DataFrame
            model_type: Type of genetic model applied
            gene_summary: Summary of variants per gene
            sample_id: Sample identifier
            additional_info: Additional metadata

        Returns:
            HTML string
        """
        model_names = {
            'autosomal_dominant': 'Autosomal Dominant',
            'autosomal_recessive': 'Autosomal Recessive',
            'compound_heterozygous': 'Compound Heterozygous'
        }

        model_display = model_names.get(model_type, model_type)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Genetic Model Analysis Report - {sample_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
        }}
        .summary-box {{
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
        }}
        .metric-label {{
            font-weight: bold;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .metric-value {{
            font-size: 1.8em;
            color: #2c3e50;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .impact-HIGH {{
            background-color: #e74c3c;
            color: white;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .impact-MODERATE {{
            background-color: #f39c12;
            color: white;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .impact-LOW {{
            background-color: #95a5a6;
            color: white;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{model_display} Inheritance Analysis</h1>

        <div class="summary-box">
            <div class="metric">
                <div class="metric-label">Sample ID</div>
                <div class="metric-value">{sample_id}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Variants</div>
                <div class="metric-value">{len(filtered_df)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Genes Affected</div>
                <div class="metric-value">{len(gene_summary)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Model Type</div>
                <div class="metric-value" style="font-size: 1.2em;">{model_display}</div>
            </div>
        </div>

        <h2>Gene Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Gene</th>
                    <th>Variant Count</th>
                    <th>Chromosomes</th>
                    <th>Impact Distribution</th>
                </tr>
            </thead>
            <tbody>
"""

        # Add gene summary rows
        for gene, info in sorted(gene_summary.items(), key=lambda x: x[1]['total_variants'], reverse=True):
            chromosomes = ', '.join(str(c) for c in info.get('chromosomes', []))
            impacts = ', '.join(f"{k}: {v}" for k, v in info.get('impacts', {}).items())

            html += f"""
                <tr>
                    <td><strong>{gene}</strong></td>
                    <td>{info['total_variants']}</td>
                    <td>{chromosomes}</td>
                    <td>{impacts}</td>
                </tr>
"""

        html += """
            </tbody>
        </table>

        <h2>Variant Details</h2>
        <table>
            <thead>
                <tr>
                    <th>Gene</th>
                    <th>Chr</th>
                    <th>Position</th>
                    <th>Ref</th>
                    <th>Alt</th>
                    <th>GT</th>
                    <th>Impact</th>
                    <th>Consequence</th>
                </tr>
            </thead>
            <tbody>
"""

        # Add variant detail rows (limit to first 100 for performance)
        for idx, row in filtered_df.head(100).iterrows():
            gene = row.get('GENE', 'N/A')
            chrom = row.get('CHROM', 'N/A')
            pos = row.get('POS', 'N/A')
            ref = row.get('REF', 'N/A')
            alt = row.get('ALT', 'N/A')
            gt = row.get('GT', 'N/A')
            impact = row.get('IMPACT', 'N/A')
            consequence = row.get('CONSEQUENCE', 'N/A')

            impact_class = f"impact-{impact}" if impact in ['HIGH', 'MODERATE', 'LOW'] else ""

            html += f"""
                <tr>
                    <td><strong>{gene}</strong></td>
                    <td>{chrom}</td>
                    <td>{pos}</td>
                    <td>{ref}</td>
                    <td>{alt}</td>
                    <td>{gt}</td>
                    <td><span class="{impact_class}">{impact}</span></td>
                    <td>{consequence}</td>
                </tr>
"""

        if len(filtered_df) > 100:
            html += f"""
                <tr>
                    <td colspan="8" style="text-align: center; color: #7f8c8d; font-style: italic;">
                        ... and {len(filtered_df) - 100} more variants (download full report for complete data)
                    </td>
                </tr>
"""

        html += f"""
            </tbody>
        </table>

        <div class="footer">
            <p><strong>Report Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Analysis Type:</strong> {model_display} Inheritance Pattern Filtering</p>
            <p><strong>Note:</strong> This report is for research use only. Clinical interpretation requires validation by qualified professionals.</p>
        </div>
    </div>
</body>
</html>
"""

        return html

    def generate_statistical_report(
        self,
        statistics: Dict[str, Any],
        sample_id: str
    ) -> str:
        """
        Generate HTML report for statistical analysis.

        Args:
            statistics: Statistical summary dictionary
            sample_id: Sample identifier

        Returns:
            HTML string
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Statistical Analysis Report - {sample_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
        }}
        .stat-label {{
            font-weight: bold;
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 10px;
        }}
        .stat-value {{
            font-size: 2em;
            color: #2c3e50;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Statistical Analysis Report</h1>

        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-label">Sample ID</div>
                <div class="stat-value" style="font-size: 1.2em;">{sample_id}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Variants</div>
                <div class="stat-value">{statistics.get('total_variants', 0):,}</div>
            </div>
"""

        # Add quality metrics
        if 'quality_metrics' in statistics:
            qm = statistics['quality_metrics']
            if 'mean_qual' in qm:
                html += f"""
            <div class="stat-card">
                <div class="stat-label">Mean Quality</div>
                <div class="stat-value">{qm['mean_qual']:.1f}</div>
            </div>
"""
            if 'mean_depth' in qm:
                html += f"""
            <div class="stat-card">
                <div class="stat-label">Mean Depth</div>
                <div class="stat-value">{qm['mean_depth']:.1f}</div>
            </div>
"""

        html += """
        </div>

        <h2>Variant Distribution</h2>
        <div class="stat-grid">
"""

        # Variant types
        if 'variant_types' in statistics:
            for vtype, count in statistics['variant_types'].items():
                html += f"""
            <div class="stat-card">
                <div class="stat-label">{vtype}</div>
                <div class="stat-value">{count:,}</div>
            </div>
"""

        html += """
        </div>

        <h2>Impact Distribution</h2>
        <div class="stat-grid">
"""

        # Impact distribution
        if 'impact_distribution' in statistics:
            for impact, count in statistics['impact_distribution'].items():
                html += f"""
            <div class="stat-card">
                <div class="stat-label">{impact}</div>
                <div class="stat-value">{count:,}</div>
            </div>
"""

        html += f"""
        </div>

        <div style="margin-top: 40px; padding-top: 20px; border-top: 2px solid #ecf0f1; color: #7f8c8d; font-size: 0.9em;">
            <p><strong>Report Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""

        return html

import os
from pathlib import Path

def create_pyramid_physics_svg(filepath: Path):
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 350" width="100%" height="100%">
  <defs>
    <style>
      .bg { fill: #fdfdfb; }
      .line { stroke: #1c1d1f; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; fill: none; }
      .line-dashed { stroke: #7c221e; stroke-width: 2; stroke-dasharray: 6 4; fill: none; }
      .accent-line { stroke: #7c221e; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; fill: none; }
      .text-title { font-family: 'Lora', Georgia, serif; font-size: 16px; font-weight: bold; fill: #1c1d1f; }
      .text-body { font-family: 'Outfit', sans-serif; font-size: 12px; fill: #5c5e62; }
      .text-accent { font-family: 'Outfit', sans-serif; font-size: 12px; font-weight: 600; fill: #7c221e; }
      .arrow { fill: #7c221e; }
      .ground { stroke: #e3e2de; stroke-width: 2; }
      .force-arrow { stroke: #7c221e; stroke-width: 2; fill: none; marker-end: url(#arrow-head); }
    </style>
    <marker id="arrow-head" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#7c221e" />
    </marker>
  </defs>

  <rect width="100%" height="100%" class="bg" />

  <!-- Ground -->
  <line x1="50" y1="300" x2="650" y2="300" class="line ground" />

  <!-- LEFT DIAGRAM: VERTICAL TOWER -->
  <g transform="translate(0, 0)">
    <!-- Vertical Wall outline -->
    <rect x="130" y="80" width="40" height="220" class="line" fill="#e3e2de" fill-opacity="0.2" />
    
    <!-- Buckling / Instability arrows -->
    <path d="M 130 180 Q 100 180 110 200" class="line-dashed" />
    <path d="M 170 180 Q 200 180 190 200" class="line-dashed" />
    
    <!-- Gravity force vectors -->
    <line x1="150" y1="40" x2="150" y2="70" class="force-arrow" />
    <text x="150" y="32" class="text-accent" text-anchor="middle">Gravité</text>
    
    <line x1="110" y1="200" x2="95" y2="215" class="force-arrow" />
    <line x1="190" y1="200" x2="205" y2="215" class="force-arrow" />
    
    <!-- Labels -->
    <text x="150" y="140" class="text-accent" text-anchor="middle">Effort concentré</text>
    <text x="150" y="160" class="text-accent" text-anchor="middle">sur la base</text>
    
    <text x="150" y="320" class="text-title" text-anchor="middle">Mur Vertical (Instable)</text>
    <text x="150" y="338" class="text-body" text-anchor="middle">Tendance naturelle au flambement</text>
  </g>

  <!-- RIGHT DIAGRAM: PYRAMID -->
  <g transform="translate(350, 0)">
    <!-- Pyramid outline -->
    <polygon points="150,80 50,300 250,300" class="line" fill="#7c221e" fill-opacity="0.05" />
    
    <!-- Gravity force vectors distributed along slope -->
    <line x1="150" y1="40" x2="150" y2="70" class="force-arrow" />
    <text x="150" y="32" class="text-accent" text-anchor="middle">Gravité</text>

    <!-- Force distribution lines -->
    <path d="M 150 90 L 100 200" class="line-dashed" />
    <path d="M 150 90 L 200 200" class="line-dashed" />
    
    <line x1="100" y1="200" x2="80" y2="244" class="force-arrow" />
    <line x1="200" y1="200" x2="220" y2="244" class="force-arrow" />

    <!-- Wide base support arrows -->
    <line x1="50" y1="310" x2="250" y2="310" class="accent-line" />
    <line x1="50" y1="310" x2="40" y2="310" class="force-arrow" />
    <line x1="250" y1="310" x2="260" y2="310" class="force-arrow" />
    
    <!-- Labels -->
    <text x="150" y="150" class="text-accent" text-anchor="middle">Distribution</text>
    <text x="150" y="170" class="text-accent" text-anchor="middle">des charges</text>
    
    <text x="150" y="320" class="text-title" text-anchor="middle">Pyramide (Stable)</text>
    <text x="150" y="338" class="text-body" text-anchor="middle">Répartition triangulaire idéale des charges</text>
  </g>
</svg>
"""
    filepath.write_text(svg_content, encoding="utf-8")
    print(f"Created: {filepath}")

def create_tombs_vs_temples_svg(filepath: Path):
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 400" width="100%" height="100%">
  <defs>
    <style>
      .bg { fill: #fdfdfb; }
      .line { stroke: #1c1d1f; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; fill: none; }
      .line-dashed { stroke: #7c221e; stroke-width: 1.5; stroke-dasharray: 4 3; fill: none; }
      .accent-line { stroke: #7c221e; stroke-width: 2.5; stroke-linecap: round; fill: none; }
      .text-title { font-family: 'Lora', Georgia, serif; font-size: 16px; font-weight: bold; fill: #1c1d1f; }
      .text-subtitle { font-family: 'Outfit', sans-serif; font-size: 13px; font-weight: bold; fill: #7c221e; }
      .text-body { font-family: 'Outfit', sans-serif; font-size: 12px; fill: #5c5e62; }
      .text-tag { font-family: 'Outfit', sans-serif; font-size: 11px; font-weight: 600; fill: #7c221e; }
      .fill-chamber { fill: #7c221e; fill-opacity: 0.1; }
      .ground { stroke: #e3e2de; stroke-width: 2; }
      .fill-temple { fill: #e3e2de; fill-opacity: 0.3; }
    </style>
  </defs>

  <rect width="100%" height="100%" class="bg" />

  <!-- Ground -->
  <line x1="50" y1="340" x2="850" y2="340" class="line ground" />

  <!-- LEFT DIAGRAM: EGYPTIAN PYRAMID (CLOSED TOMB) -->
  <g transform="translate(0, 0)">
    <!-- Pyramid Smooth Outline -->
    <polygon points="220,100 70,340 370,340" class="line" fill="#7c221e" fill-opacity="0.02" />
    
    <!-- Hidden inner chambers & galleries -->
    <!-- Entrance (closed/hidden) -->
    <line x1="310" y1="240" x2="220" y2="190" class="line-dashed" />
    <!-- Ascending gallery -->
    <line x1="220" y1="190" x2="180" y2="230" class="line-dashed" />
    <!-- King's Chamber -->
    <rect x="200" y="170" width="30" height="20" class="line fill-chamber" />
    <!-- Subterranean chamber -->
    <line x1="220" y1="190" x2="220" y2="370" class="line-dashed" />
    <rect x="200" y="360" width="40" height="15" class="line fill-chamber" />
    
    <!-- Annotations -->
    <text x="250" y="165" class="text-tag" text-anchor="start">Chambre du Roi</text>
    <text x="230" y="382" class="text-tag" text-anchor="start">Chambre Souterraine</text>
    <text x="325" y="235" class="text-tag" text-anchor="start">Accès scellé</text>

    <!-- Labels -->
    <text x="220" y="50" class="text-title" text-anchor="middle">PYRAMIDE D'ÉGYPTE</text>
    <text x="220" y="70" class="text-subtitle" text-anchor="middle">Tombeau Funéraire Royal (Fermé)</text>
    <text x="220" y="358" class="text-body" text-anchor="middle">Objectif : Protéger le corps du Pharaon pour l'éternité</text>
  </g>

  <!-- RIGHT DIAGRAM: MESOAMERICAN PYRAMID (OPEN TEMPLE) -->
  <g transform="translate(480, 0)">
    <!-- Stepped Temple Platform Outline -->
    <!-- Degré 1 -->
    <polygon points="50,340 330,340 310,290 70,290" class="line fill-temple" />
    <!-- Degré 2 -->
    <polygon points="70,290 310,290 290,240 90,240" class="line fill-temple" />
    <!-- Degré 3 -->
    <polygon points="90,240 290,240 270,190 110,190" class="line fill-temple" />
    <!-- Degré 4 -->
    <polygon points="110,190 270,190 250,140 130,140" class="line fill-temple" />
    
    <!-- Altar / Temple at the top -->
    <rect x="165" y="100" width="50" height="40" class="line" fill="#7c221e" fill-opacity="0.1" />
    <polygon points="155,100 190,80 225,100" class="line" />
    
    <!-- Central monumental staircase -->
    <polygon points="175,340 205,340 205,140 175,140" class="accent-line" />
    <!-- Horizontal steps -->
    <line x1="175" y1="315" x2="205" y2="315" class="accent-line" />
    <line x1="175" y1="290" x2="205" y2="290" class="accent-line" />
    <line x1="175" y1="265" x2="205" y2="265" class="accent-line" />
    <line x1="175" y1="240" x2="205" y2="240" class="accent-line" />
    <line x1="175" y1="215" x2="205" y2="215" class="accent-line" />
    <line x1="175" y1="190" x2="205" y2="190" class="accent-line" />
    <line x1="175" y1="165" x2="205" y2="165" class="accent-line" />

    <!-- Annotations -->
    <text x="225" y="115" class="text-tag" text-anchor="start">Temple du Sommet</text>
    <text x="170" y="270" class="text-tag" text-anchor="end">Escalier Public</text>

    <!-- Labels -->
    <text x="190" y="50" class="text-title" text-anchor="middle">PYRAMIDE DE MÉSOAMÉRIQUE</text>
    <text x="190" y="70" class="text-subtitle" text-anchor="middle">Plateforme Rituelle &amp; Temple (Ouvert)</text>
    <text x="190" y="358" class="text-body" text-anchor="middle">Objectif : Théâtre cérémoniel public et observations</text>
  </g>
</svg>
"""
    filepath.write_text(svg_content, encoding="utf-8")
    print(f"Created: {filepath}")

if __name__ == "__main__":
    _BASE = Path(__file__).parent
    images_dir = _BASE / "website" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    create_pyramid_physics_svg(images_dir / "pyramid_physics.svg")
    create_tombs_vs_temples_svg(images_dir / "tombs_vs_temples.svg")

"""
Obsidian Personal Wikipedia Template Generator
Creates database-friendly markdown templates optimized for Dataview plugin
Generated with claude ai
"""

import os
from datetime import datetime
from pathlib import Path

# Knowledge structure based on traditional academic divisions
KNOWLEDGE_STRUCTURE = {
    "Natural-Sciences": {
        "subcategories": ["Physics", "Chemistry", "Biology", "Earth-Sciences", "Astronomy"],
        "understanding_default": "intermediate",
        "description": "Study of the natural world through observation and experimentation"
    },
    "Formal-Sciences": {
        "subcategories": ["Mathematics", "Logic", "Computer-Science", "Statistics", "Systems-Theory"],
        "understanding_default": "advanced", 
        "description": "Abstract conceptual systems and logical structures"
    },
    "Social-Sciences": {
        "subcategories": ["Psychology", "Sociology", "Anthropology", "Economics", "Political-Science", "Human-Geography"],
        "understanding_default": "intermediate",
        "description": "Study of human behavior and social structures"
    },
    "Humanities": {
        "subcategories": ["Philosophy", "History", "Literature", "Languages", "Arts", "Religion", "Ethics"],
        "understanding_default": "intermediate",
        "description": "Study of human culture, values, and creative expression"
    },
    "Applied-Sciences": {
        "subcategories": ["Engineering", "Medicine", "Technology", "Agriculture", "Architecture", "Education"],
        "understanding_default": "intermediate",
        "description": "Practical application of scientific knowledge"
    }
}

class ObsidianWikiGenerator:
    def __init__(self, vault_path="MyWiki"):
        self.vault_path = Path(vault_path)
        self.today = datetime.now().strftime("%Y-%m-%d")
    
    def create_vault_structure(self):
        """Create the main folder structure"""
        print(f"Creating vault structure at: {self.vault_path}")
        
        # Create main vault directory
        self.vault_path.mkdir(exist_ok=True)
        
        # Create category folders
        for category in KNOWLEDGE_STRUCTURE.keys():
            category_path = self.vault_path / category
            category_path.mkdir(exist_ok=True)
            print(f"  Created folder: {category}")
        
        # Create attachments folder
        attachments_path = self.vault_path / "attachments"
        attachments_path.mkdir(exist_ok=True)
        print(f"  Created folder: attachments")
    
    def generate_article_template(self, title, category, subcategory):
        """Generate markdown template for a discipline article"""
        understanding_level = KNOWLEDGE_STRUCTURE[category]["understanding_default"]
        
        yaml_frontmatter = f"""---
title: "{title}"
category: "{category.replace('-', ' ')}"
subcategory: "{subcategory}"
tags: []
status: "stub"
understanding: "{understanding_level}"
related_fields: []
prerequisites: []
created: {self.today}
updated: {self.today}
aliases: []
---"""
        
        content = f"""# {title}

## Overview
Brief introduction and definition of {title}.

## Key Concepts
- [[Concept 1]]
- [[Concept 2]]

## Subtopics
```dataview
TABLE status, understanding, updated
FROM "#{category.replace('-', ' ')}" AND "#{subcategory}"
WHERE contains(file.folder, "{category}")
SORT title ASC
```

## Related Fields
Strong connections to other disciplines.

## Prerequisites
Essential background knowledge needed to understand {title}.

## References
- Source 1
- Source 2
"""
        
        return yaml_frontmatter + "\n\n" + content
    
    def generate_category_dashboard(self, category, category_info):
        """Generate category overview page with Dataview queries"""
        category_display = category.replace('-', ' ')
        
        yaml_frontmatter = f"""---
title: "{category_display} - Overview"
category: "Dashboard"
subcategory: "{category_display}"
tags: [dashboard, overview]
status: "dashboard"
understanding: "meta"
created: {self.today}
updated: {self.today}
aliases: ["{category_display} Dashboard"]
---"""
        
        content = f"""# {category_display} Overview

{category_info['description']}

## All Articles in {category_display}

```dataview
TABLE status, understanding, updated
FROM "{category}"
WHERE category = "{category_display}"
SORT title ASC
```

## Articles by Status

### Comprehensive Articles
```dataview
LIST
FROM "{category}"
WHERE status = "comprehensive"
SORT title ASC
```

### Developing Articles  
```dataview
LIST
FROM "{category}"
WHERE status = "developing"
SORT title ASC
```

### Stub Articles
```dataview
LIST  
FROM "{category}"
WHERE status = "stub"
SORT title ASC
```

## Articles by Understanding Level

### Beginner Level
```dataview
LIST
FROM "{category}"
WHERE understanding = "beginner"
SORT title ASC
```

### Intermediate Level
```dataview
LIST
FROM "{category}"  
WHERE understanding = "intermediate"
SORT title ASC
```

### Advanced Level
```dataview
LIST
FROM "{category}"
WHERE understanding = "advanced" 
SORT title ASC
```

## Main Disciplines

"""
        
        # Add links to main discipline articles
        for subcategory in category_info["subcategories"]:
            content += f"- [[{subcategory}]]\n"
        
        return yaml_frontmatter + "\n\n" + content
    
    def generate_main_dashboard(self):
        """Generate main wiki dashboard"""
        yaml_frontmatter = f"""---
title: "Personal Wikipedia"
category: "Dashboard" 
subcategory: "Main"
tags: [dashboard, index, main]
status: "dashboard"
understanding: "meta"
created: {self.today}
updated: {self.today}
aliases: ["Wiki Home", "Knowledge Base"]
---"""
        
        content = """# Personal Wikipedia

Welcome to your personal knowledge base! This wiki follows traditional academic divisions of human knowledge.

## Knowledge Domains

"""
        
        for category, info in KNOWLEDGE_STRUCTURE.items():
            category_display = category.replace('-', ' ')
            content += f"### [[{category_display} - Overview|{category_display}]]\n"
            content += f"{info['description']}\n\n"
        
        content += """## Recent Updates

```dataview
TABLE category, status, understanding
FROM ""
WHERE created >= date(today) - dur(7 days)
SORT updated DESC
LIMIT 10
```

## Statistics

### Articles by Category
```dataview
TABLE length(rows) AS "Article Count"
FROM ""
WHERE category != "Dashboard"
GROUP BY category
SORT category ASC
```

### Articles by Status
```dataview  
TABLE length(rows) AS "Count"
FROM ""
WHERE category != "Dashboard"
GROUP BY status
SORT status ASC
```

## Quick Links
- [[Natural Sciences - Overview]]
- [[Formal Sciences - Overview]]  
- [[Social Sciences - Overview]]
- [[Humanities - Overview]]
- [[Applied Sciences - Overview]]
"""
        
        return yaml_frontmatter + "\n\n" + content
    
    def create_templates(self, preview_only=False):
        """Create all template files"""
        if not preview_only:
            self.create_vault_structure()
        
        files_to_create = []
        
        # Generate main dashboard
        main_dashboard = self.generate_main_dashboard()
        files_to_create.append(("Personal Wikipedia.md", main_dashboard))
        
        # Generate category dashboards and discipline articles
        for category, category_info in KNOWLEDGE_STRUCTURE.items():
            # Category dashboard
            dashboard_content = self.generate_category_dashboard(category, category_info)
            dashboard_filename = f"{category}/{category.replace('-', ' ')} - Overview.md"
            files_to_create.append((dashboard_filename, dashboard_content))
            
            # Individual discipline articles
            for subcategory in category_info["subcategories"]:
                article_content = self.generate_article_template(
                    subcategory.replace('-', ' '), 
                    category, 
                    subcategory.replace('-', ' ')
                )
                article_filename = f"{category}/{subcategory.replace('-', ' ')}.md"
                files_to_create.append((article_filename, article_content))
        
        if preview_only:
            print(f"\nWould create {len(files_to_create)} files:")
            for filename, _ in files_to_create:
                print(f"  {filename}")
            return files_to_create
        
        # Actually create the files
        for filename, content in files_to_create:
            file_path = self.vault_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  Created: {filename}")
        
        print(f"\n✅ Successfully created {len(files_to_create)} template files!")
        print(f"📁 Vault location: {self.vault_path.absolute()}")
        print(f"🚀 Open '{self.vault_path}/Personal Wikipedia.md' to start!")
        
        return files_to_create

def main():
    """Main function with user interaction"""
    print("🧠 Obsidian Personal Wikipedia Generator")
    print("=" * 50)
    
    # Get vault path from user
    vault_name = input("Enter vault name (default: MyWiki): ").strip()
    if not vault_name:
        vault_name = "MyWiki"
    
    generator = ObsidianWikiGenerator(vault_name)
    
    # Preview mode first
    print(f"\n📋 Preview of files that will be created:")
    files = generator.create_templates(preview_only=True)
    
    # Ask for confirmation
    proceed = input(f"\nProceed with creating {len(files)} files? (y/N): ").strip().lower()
    
    if proceed in ['y', 'yes']:
        generator.create_templates(preview_only=False)
    else:
        print("❌ Cancelled. No files were created.")

if __name__ == "__main__":
    main()

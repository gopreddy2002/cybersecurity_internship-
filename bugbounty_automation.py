#!/usr/bin/env python3
"""
Bug Bounty Automation Framework for Windows
Automates reconnaissance workflow using tools from awesome-bugbounty-tools
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import json

class BugBountyAutomator:
    def __init__(self, target_domain):
        self.target = target_domain
        self.results_dir = Path(f"results\\{target_domain}")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.results_dir / "recon_log.txt"
        
        # Create log file
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"Bug Bounty Recon Started: {datetime.now()}\n")
            f.write(f"Target: {target_domain}\n")
            f.write("=" * 50 + "\n\n")
    
    def log(self, message, level="INFO"):
        """Log messages to console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    
    def run_command(self, cmd, output_file=None, check=True, capture_output=False):
        """Run a command-line tool"""
        self.log(f"Running: {' '.join(cmd)}")
        
        try:
            if capture_output:
                result = subprocess.run(
                    cmd, 
                    check=check, 
                    text=True,
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                return result
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    result = subprocess.run(
                        cmd, 
                        stdout=f, 
                        stderr=subprocess.PIPE, 
                        check=check, 
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                    )
                return result
            else:
                result = subprocess.run(
                    cmd, 
                    check=check, 
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                return result
        except subprocess.CalledProcessError as e:
            self.log(f"Error running command: {e}", level="ERROR")
            return None
        except FileNotFoundError:
            self.log(f"Tool not found: {cmd[0]}. Install it first.", level="ERROR")
            return None
    
    def check_tool_installed(self, tool_name):
        """Check if a tool is installed"""
        try:
            subprocess.run([tool_name, "--help"], 
                          capture_output=True, check=False)
            return True
        except FileNotFoundError:
            return False
    
    # ============================================
    # PHASE 1: SUBDOMAIN ENUMERATION
    # ============================================
    def subfinder_enum(self):
        """Subfinder - subdomain discovery using DNS enumeration"""
        self.log("Starting Subfinder subdomain enumeration...")
        output = self.results_dir / "subfinder_subdomains.txt"
        
        result = self.run_command([
            "subfinder.exe", 
            "-d", self.target,
            "-o", str(output), 
            "-silent"
        ])
        
        if result and output.exists():
            count = sum(1 for line in open(output, encoding='utf-8') if line.strip())
            self.log(f"Subfinder found {count} subdomains")
            return output
        return None
    
    def amass_enum(self):
        """Amass - in-depth attack surface mapping"""
        self.log("Starting Amass subdomain enumeration...")
        output = self.results_dir / "amass_subdomains.txt"
        
        result = self.run_command([
            "amass.exe", 
            "enum", 
            "-d", self.target,
            "-o", str(output)
        ])
        
        if result and output.exists():
            count = sum(1 for line in open(output, encoding='utf-8') if line.strip())
            self.log(f"Amass found {count} subdomains")
            return output
        return None
    
    def subdomain_enumeration(self):
        """Run all subdomain enumeration tools and merge results"""
        self.log("\n" + "="*50, level="INFO")
        self.log("PHASE 1: SUBDOMAIN ENUMERATION", level="INFO")
        self.log("="*50, level="INFO")
        
        # Run tools
        subfinder_file = self.subfinder_enum()
        amass_file = self.amass_enum()
        
        # Merge and deduplicate
        all_subdomains = set()
        
        for f in [subfinder_file, amass_file]:
            if f and f.exists():
                with open(f, encoding='utf-8') as fp:
                    for line in fp:
                        line = line.strip()
                        if line and line != '':
                            all_subdomains.add(line)
        
        # Save merged results
        merged_file = self.results_dir / "subdomains.txt"
        with open(merged_file, 'w', encoding='utf-8') as f:
            for subdomain in sorted(all_subdomains):
                f.write(subdomain + '\n')
        
        self.log(f"\n✅ Total unique subdomains found: {len(all_subdomains)}")
        self.log(f"Saved to: {merged_file}")
        
        return merged_file
    
    # ============================================
    # PHASE 2: PORT SCANNING
    # ============================================
    def naabu_scan(self):
        """Naabu - fast port scanner"""
        self.log("Starting Naabu port scanning...")
        
        subdomains_file = self.results_dir / "subdomains.txt"
        if not subdomains_file.exists():
            self.log("No subdomains file found, skipping Naabu", level="WARNING")
            return None
        
        output = self.results_dir / "naabu_ports.txt"
        
        result = self.run_command([
            "naabu.exe", 
            "-list", str(subdomains_file),
            "-o", str(output), 
            "-silent"
        ])
        
        if result and output.exists():
            count = sum(1 for line in open(output, encoding='utf-8') if line.strip())
            self.log(f"Naabu found {count} open ports")
            return output
        return None
    
    def port_scanning(self):
        """Run port scanning"""
        self.log("\n" + "="*50, level="INFO")
        self.log("PHASE 2: PORT SCANNING", level="INFO")
        self.log("="*50, level="INFO")
        
        naabu_file = self.naabu_scan()
        if naabu_file:
            self.log(f"Saved to: {naabu_file}")
        
        return naabu_file
    
    # ============================================
    # PHASE 3: TECHNOLOGY DETECTION
    # ============================================
    def httpx_technology(self):
        """httpx - technology detection, status codes, titles"""
        self.log("Starting httpx technology detection...")
        
        subdomains_file = self.results_dir / "subdomains.txt"
        if not subdomains_file.exists():
            self.log("No subdomains file found, skipping httpx", level="WARNING")
            return None
        
        output = self.results_dir / "technologies.txt"
        
        result = self.run_command([
            "httpx.exe", 
            "-l", str(subdomains_file),
            "-tech-detect",
            "-status-code",
            "-title",
            "-o", str(output)
        ])
        
        if result and output.exists():
            count = sum(1 for line in open(output, encoding='utf-8') if line.strip())
            self.log(f"Technologies detected for {count} domains")
            return output
        return None
    
    def technology_detection(self):
        """Run technology detection"""
        self.log("\n" + "="*50, level="INFO")
        self.log("PHASE 3: TECHNOLOGY DETECTION", level="INFO")
        self.log("="*50, level="INFO")
        
        tech_file = self.httpx_technology()
        if tech_file:
            self.log(f"Saved to: {tech_file}")
        
        return tech_file
    
    # ============================================
    # PHASE 4: VULNERABILITY SCANNING
    # ============================================
    def nuclei_scan(self):
        """Nuclei - template-based vulnerability scanner"""
        self.log("Starting Nuclei vulnerability scanning...")
        
        subdomains_file = self.results_dir / "subdomains.txt"
        if not subdomains_file.exists():
            self.log("No subdomains file found, skipping Nuclei", level="WARNING")
            return None
        
        output = self.results_dir / "nuclei_results.json"
        
        result = self.run_command([
            "nuclei.exe", 
            "-l", str(subdomains_file),
            "-json",
            "-o", str(output),
            "-severity", "high,medium"
        ])
        
        if result and output.exists():
            self.log(f"Vulnerabilities saved to: {output}")
            
            try:
                with open(output, encoding='utf-8') as f:
                    vulns = json.load(f)
                    self.log(f"Found {len(vulns)} vulnerabilities")
            except:
                pass
            return output
        return None
    
    def vulnerability_scanning(self):
        """Run vulnerability scanning"""
        self.log("\n" + "="*50, level="INFO")
        self.log("PHASE 4: VULNERABILITY SCANNING", level="INFO")
        self.log("="*50, level="INFO")
        
        nuclei_file = self.nuclei_scan()
        if nuclei_file:
            self.log(f"Saved to: {nuclei_file}")
        
        return nuclei_file
    
    # ============================================
    # PHASE 5: CONTENT DISCOVERY
    # ============================================
    def feroxbuster_scan(self):
        """feroxbuster - content discovery"""
        self.log("Starting feroxbuster content discovery...")
        
        result = self.run_command([
            "feroxbuster.exe", 
            "-u", f"https://{self.target}",
            "-o", str(self.results_dir / "feroxbuster_main.txt"),
            "-q"
        ])
        
        self.log("feroxbuster scan complete")
        return self.results_dir / "feroxbuster_main.txt"
    
    def content_discovery(self):
        """Run content discovery"""
        self.log("\n" + "="*50, level="INFO")
        self.log("PHASE 5: CONTENT DISCOVERY", level="INFO")
        self.log("="*50, level="INFO")
        
        ferox_file = self.feroxbuster_scan()
        if ferox_file and ferox_file.exists():
            self.log(f"Saved to: {ferox_file}")
        
        return ferox_file
    
    # ============================================
    # UTILITY FUNCTIONS
    # ============================================
    def generate_summary(self):
        """Generate summary report of all findings"""
        self.log("\n" + "="*50, level="INFO")
        self.log("GENERATING SUMMARY REPORT", level="INFO")
        self.log("="*50, level="INFO")
        
        report_file = self.results_dir / "SUMMARY_REPORT.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"BUG BOUNTY RECON REPORT\n")
            f.write(f"Target: {self.target}\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("=" * 60 + "\n\n")
            
            findings = {
                "Subdomains": self.results_dir / "subdomains.txt",
                "Ports": self.results_dir / "naabu_ports.txt",
                "Technologies": self.results_dir / "technologies.txt",
                "Vulnerabilities": self.results_dir / "nuclei_results.json"
            }
            
            for name, filepath in findings.items():
                if filepath.exists():
                    count = sum(1 for line in open(filepath, encoding='utf-8') if line.strip())
                    f.write(f"{name}: {count} findings\n")
                    f.write(f"  Location: {filepath}\n\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("✅ Reconnaissance Complete!\n")
        
        self.log(f"Summary report saved to: {report_file}")
        return report_file
    
    def print_subdomains(self):
        """Print all discovered subdomains"""
        subdomains_file = self.results_dir / "subdomains.txt"
        if subdomains_file.exists():
            print("\n" + "="*50)
            print("DISCOVERED SUBDOMAINS:")
            print("="*50)
            with open(subdomains_file, encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        print(f"  {line.strip()}")
            print("="*50)
    
    # ============================================
    # MAIN WORKFLOW
    # ============================================
    def run_full_recon(self):
        """Run complete reconnaissance workflow"""
        start_time = datetime.now()
        self.log(f"\n🚀 STARTING BUG BOUNTY RECON FOR: {self.target}")
        self.log(f"Start Time: {start_time}")
        
        self.subdomain_enumeration()
        self.port_scanning()
        self.technology_detection()
        self.vulnerability_scanning()
        self.content_discovery()
        
        self.generate_summary()
        self.print_subdomains()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        self.log(f"\n✅ RECON COMPLETE!")
        self.log(f"End Time: {end_time}")
        self.log(f"Duration: {duration}")
        self.log(f"Results saved to: {self.results_dir}")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("\n" + "="*50)
        print("BUG BOUNTY AUTOMATION TOOL (Windows)")
        print("="*50)
        print("\nUsage: python bugbounty_automation.py <target-domain>")
        print("\nExamples:")
        print("  python bugbounty_automation.py example.com")
        print("  python bugbounty_automation.py target-site.io")
        print("\n" + "="*50)
        sys.exit(1)
    
    target = sys.argv[1]
    
    print("\n" + "="*50)
    print("🎯 BUG BOUNTY AUTOMATION FRAMEWORK")
    print("="*50)
    print(f"Target: {target}")
    print("="*50 + "\n")
    
    automator = BugBountyAutomator(target)
    automator.run_full_recon()


if __name__ == "__main__":
    main()
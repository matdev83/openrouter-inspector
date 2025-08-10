"""HTML parser for extracting provider data from OpenRouter web pages."""

import re
from typing import List, Optional
from datetime import datetime

from bs4 import BeautifulSoup, Tag
from bs4.element import ResultSet

from .models import WebProviderData


class OpenRouterWebParser:
    """Parser for extracting provider data from OpenRouter web pages."""

    @staticmethod
    def parse_model_page(html_content: str, model_id: str) -> List[WebProviderData]:
        """
        Parse provider data from a model's web page.
        
        Args:
            html_content: Raw HTML content from the model page
            model_id: The model identifier for context
            
        Returns:
            List of WebProviderData objects extracted from the page
            
        Raises:
            ValueError: If HTML content is invalid or cannot be parsed
        """
        if not html_content or not html_content.strip():
            raise ValueError("HTML content cannot be empty")
            
        try:
            soup = BeautifulSoup(html_content, 'lxml')
        except Exception as e:
            raise ValueError(f"Failed to parse HTML content: {e}")
        
        providers: List[WebProviderData] = []
        
        # Look for provider tables - try multiple common patterns
        provider_tables = OpenRouterWebParser._find_provider_tables(soup)
        
        for table in provider_tables:
            table_providers = OpenRouterWebParser._extract_providers_from_table(table)
            providers.extend(table_providers)
        
        # Try alternative parsing methods to find additional providers
        alternative_providers = OpenRouterWebParser._extract_providers_alternative(soup)
        
        # Merge providers, avoiding duplicates based on unique provider keys
        existing_keys = {OpenRouterWebParser._create_provider_key(p) for p in providers}
        for alt_provider in alternative_providers:
            alt_key = OpenRouterWebParser._create_provider_key(alt_provider)
            if alt_key not in existing_keys:
                providers.append(alt_provider)
        
        return providers

    @staticmethod
    def _find_provider_tables(soup: BeautifulSoup) -> List[Tag]:
        """Find provider tables in the HTML using various selectors."""
        tables = []
        seen_tables = set()
        
        # Common table selectors for provider data
        selectors = [
            '.provider-table',  # Class-based selector
            '#providers',  # ID-based selector
            '[data-testid*="provider"]',  # Data attribute selector
            'table',  # Generic table (last resort)
        ]
        
        for selector in selectors:
            try:
                found_tables = soup.select(selector)
                for table in found_tables:
                    if isinstance(table, Tag) and table.name == 'table':
                        # Use table's position in DOM as unique identifier
                        table_id = id(table)
                        if table_id not in seen_tables:
                            # Verify this looks like a provider table
                            if OpenRouterWebParser._is_provider_table(table):
                                tables.append(table)
                                seen_tables.add(table_id)
            except Exception:
                # Continue with other selectors if one fails
                continue
        
        return tables

    @staticmethod
    def _is_provider_table(table: Tag) -> bool:
        """Check if a table appears to contain provider data."""
        # Look for headers that suggest this is a provider table
        header_row = table.find('tr')
        if not header_row:
            return False
            
        headers: List[Tag] = header_row.find_all(['th', 'td'])  # type: ignore[assignment]
        header_text = ' '.join([h.get_text().lower() for h in headers])
        
        # Must have "provider" and at least one performance metric
        has_provider = 'provider' in header_text or 'service' in header_text or 'name' in header_text
        has_metrics = any(indicator in header_text for indicator in [
            'throughput', 'latency', 'uptime', 'tps', 'response time', 'availability', 'performance'
        ])
        
        return has_provider and has_metrics

    @staticmethod
    def _extract_providers_from_table(table: Tag) -> List[WebProviderData]:
        """Extract provider data from a table element."""
        providers = []
        
        # Find header row to understand column structure
        header_row = table.find('tr')
        if not header_row:
            return providers
            
        headers = [th.get_text().strip().lower() for th in header_row.find_all(['th', 'td'])]
        
        # Map column indices
        col_indices = OpenRouterWebParser._map_column_indices(headers)
        
        # Process data rows
        rows: List[Tag] = list(table.find_all('tr'))[1:]
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:  # Need at least provider name and one metric
                continue
                
            provider_data = OpenRouterWebParser._extract_provider_from_row(cells, col_indices)
            if provider_data:
                providers.append(provider_data)
        
        return providers

    @staticmethod
    def _map_column_indices(headers: List[str]) -> dict[str, int]:
        """Map column headers to their indices."""
        indices: dict[str, int] = {}
        
        for i, header in enumerate(headers):
            header_lower = header.lower().strip()
            
            # Provider name column (be more specific to avoid conflicts)
            if header_lower in ['provider', 'provider name', 'service', 'name'] or \
               (('provider' in header_lower or 'service' in header_lower) and 'name' in header_lower):
                if 'provider' not in indices:  # Take first match
                    indices['provider'] = i
            
            # Quantization column
            elif any(term in header_lower for term in ['quantization', 'quant', 'precision']):
                if 'quantization' not in indices:
                    indices['quantization'] = i
            
            # Context window column
            elif any(term in header_lower for term in ['context', 'ctx', 'window']):
                if 'context' not in indices:
                    indices['context'] = i
            
            # Max output/completion tokens column
            elif any(term in header_lower for term in ['max output', 'max completion', 'max tokens', 'output limit']):
                if 'max_output' not in indices:
                    indices['max_output'] = i
            
            # Throughput column
            elif any(term in header_lower for term in ['throughput', 'tps']) or \
                 header_lower in ['tokens/s', 'tokens per second', 't/s']:
                if 'throughput' not in indices:
                    indices['throughput'] = i
            
            # Latency column (be specific to avoid matching "time" in other contexts)
            elif any(term in header_lower for term in ['latency', 'response time', 'delay']) or \
                 (header_lower == 'time' and 'latency' not in indices):
                if 'latency' not in indices:
                    indices['latency'] = i
            
            # Uptime column
            elif any(term in header_lower for term in ['uptime', 'availability', 'online']) or \
                 (header_lower == 'up' and 'uptime' not in indices):
                if 'uptime' not in indices:
                    indices['uptime'] = i
        
        return indices

    @staticmethod
    def _extract_provider_from_row(cells: List[Tag], col_indices: dict) -> Optional[WebProviderData]:
        """Extract provider data from a table row."""
        if 'provider' not in col_indices or col_indices['provider'] >= len(cells):
            return None
            
        provider_name = cells[col_indices['provider']].get_text().strip()
        if not provider_name:
            return None
        
        # Extract quantization
        quantization = None
        if 'quantization' in col_indices and col_indices['quantization'] < len(cells):
            quantization_text = cells[col_indices['quantization']].get_text().strip()
            if quantization_text and quantization_text not in ['—', '-', 'N/A', '']:
                quantization = quantization_text
        
        # Extract context window
        context_window = None
        if 'context' in col_indices and col_indices['context'] < len(cells):
            context_text = cells[col_indices['context']].get_text().strip()
            context_window = OpenRouterWebParser.parse_context_window(context_text)
        
        # Extract max output tokens
        max_completion_tokens = None
        if 'max_output' in col_indices and col_indices['max_output'] < len(cells):
            max_output_text = cells[col_indices['max_output']].get_text().strip()
            max_completion_tokens = OpenRouterWebParser.parse_context_window(max_output_text)
        
        # Extract metrics
        throughput = None
        if 'throughput' in col_indices and col_indices['throughput'] < len(cells):
            throughput_text = cells[col_indices['throughput']].get_text().strip()
            throughput = OpenRouterWebParser.parse_throughput(throughput_text)
        
        latency = None
        if 'latency' in col_indices and col_indices['latency'] < len(cells):
            latency_text = cells[col_indices['latency']].get_text().strip()
            latency = OpenRouterWebParser.parse_latency(latency_text)
        
        uptime = None
        if 'uptime' in col_indices and col_indices['uptime'] < len(cells):
            uptime_text = cells[col_indices['uptime']].get_text().strip()
            uptime = OpenRouterWebParser.parse_uptime(uptime_text)
        
        return WebProviderData(
            provider_name=provider_name,
            quantization=quantization,
            context_window=context_window,
            max_completion_tokens=max_completion_tokens,
            throughput_tps=throughput,
            latency_seconds=latency,
            uptime_percentage=uptime,
            last_scraped=datetime.now()
        )

    @staticmethod
    def _extract_providers_alternative(soup: BeautifulSoup) -> List[WebProviderData]:
        """Alternative extraction method when no tables are found."""
        providers = []
        seen_providers = set()
        
        # Look for div-based layouts or other structures
        # This is a fallback for non-table layouts
        provider_containers: ResultSet = soup.find_all(['div', 'section'], class_=re.compile(r'provider-offer|provider-card|offer|card'))
        
        # Filter out containers that are too large (likely parent containers)
        filtered_containers: List[Tag] = []
        for container in provider_containers:
            text_length = len(container.get_text())
            # Skip containers that are too large (likely contain multiple providers)
            # Also skip containers that contain multiple provider names
            text_content = container.get_text().lower()
            # Count actual provider names, not just the word "provider"
            provider_name_count = 0
            for name in ['provider1', 'provider2', 'provider3', 'provider4', 'cardprovider1', 'cardprovider2']:
                if name in text_content:
                    provider_name_count += 1
            
            # Accept containers that are reasonably sized and don't contain too many providers
            if text_length < 150 or provider_name_count <= 1:
                filtered_containers.append(container)
        
        provider_containers = filtered_containers
        
        # Only try alternative parsing if we find containers that look like provider cards
        if provider_containers:
            for container in provider_containers:
                provider_data = OpenRouterWebParser._extract_provider_from_container(container)
                if provider_data:
                    # Create unique key for this provider offer
                    provider_key = OpenRouterWebParser._create_provider_key(provider_data)
                    if provider_key not in seen_providers:
                        providers.append(provider_data)
                        seen_providers.add(provider_key)
        
        return providers

    @staticmethod
    def _extract_provider_from_container(container: Tag) -> Optional[WebProviderData]:
        """Extract provider data from a non-table container."""
        # Look for provider name
        provider_name = None
        name_selectors = [
            '.provider-name', '.name', 'h3', 'h4', '.title',
            '[data-testid*="provider"]', '[data-testid*="name"]'
        ]
        
        for selector in name_selectors:
            name_elem = container.select_one(selector)
            if name_elem:
                provider_name = name_elem.get_text().strip()
                break
        
        if not provider_name:
            return None
        
        # Extract metrics from text content
        text_content = container.get_text()
        
        throughput = OpenRouterWebParser._extract_metric_from_text(text_content, 'throughput')
        latency = OpenRouterWebParser._extract_metric_from_text(text_content, 'latency')
        uptime = OpenRouterWebParser._extract_metric_from_text(text_content, 'uptime')
        
        return WebProviderData(
            provider_name=provider_name,
            quantization=None,  # Not typically available in card layouts
            context_window=None,  # Not typically available in card layouts
            max_completion_tokens=None,  # Not typically available in card layouts
            throughput_tps=throughput,
            latency_seconds=latency,
            uptime_percentage=uptime,
            last_scraped=datetime.now()
        )

    @staticmethod
    def _extract_metric_from_text(text: str, metric_type: str) -> Optional[float]:
        """Extract a specific metric from text content."""
        if metric_type == 'throughput':
            # Look for patterns like "15.2 TPS", "12 tokens/s", "Performance: 18.9 tokens per second", etc.
            patterns = [
                r'(\d+\.?\d*)\s*tps',
                r'(\d+\.?\d*)\s*tokens?[/\s]s(?:ec|ond)?',
                r'(\d+\.?\d*)\s*tokens?\s+per\s+second',
                r'throughput[:\s]+(\d+\.?\d*)',
                r'performance[:\s]+(\d+\.?\d*)\s*(?:tps|tokens?[/\s]s|tokens?\s+per\s+second)',
                r'tps[:\s]+(\d+\.?\d*)',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return float(match.group(1))
        
        elif metric_type == 'latency':
            # Look for patterns like "0.85s", "850ms", "1.2 seconds", "Response time: 950ms", etc.
            patterns = [
                r'(\d+\.?\d*)\s*ms',  # milliseconds
                r'(\d+\.?\d*)\s*s(?:ec|onds?)?',  # seconds
                r'latency[:\s]+(\d+\.?\d*)',
                r'response\s+time[:\s]+(\d+\.?\d*)\s*ms',
                r'response\s+time[:\s]+(\d+\.?\d*)\s*s(?:ec|onds?)?',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = float(match.group(1))
                    # Convert milliseconds to seconds
                    if 'ms' in match.group(0).lower():
                        value = value / 1000
                    return value
        
        elif metric_type == 'uptime':
            # Look for patterns like "99.5%", "uptime: 98.2%", "Availability: 98.5%", etc.
            patterns = [
                r'(\d+\.?\d*)\s*%',
                r'uptime[:\s]+(\d+\.?\d*)',
                r'availability[:\s]+(\d+\.?\d*)',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return float(match.group(1))
        
        return None

    @staticmethod
    def parse_context_window(text: str) -> Optional[int]:
        """
        Parse context window value from text.
        
        Args:
            text: Text containing context window information (e.g., '33K', '16384', '1M')
            
        Returns:
            Context window value in tokens, or None if parsing fails
        """
        if not text or text.strip() in ['—', '-', 'N/A', '']:
            return None
        
        # Remove extra whitespace and convert to lowercase
        text = text.strip().lower()
        
        # Patterns for different context window formats
        patterns = [
            (r'(\d+\.?\d*)\s*k', 1000),  # "33K" -> 33000
            (r'(\d+\.?\d*)\s*m', 1000000),  # "1M" -> 1000000
            (r'^(\d+)$', 1),  # Just a number
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1))
                    return int(value * multiplier)
                except ValueError:
                    continue
        
        return None

    @staticmethod
    def parse_throughput(text: str) -> Optional[float]:
        """
        Parse throughput value from text.
        
        Args:
            text: Text containing throughput information (e.g., '15.2 TPS', '12 tokens/s')
            
        Returns:
            Throughput value in tokens per second, or None if parsing fails
        """
        if not text or text.strip() in ['—', '-', 'N/A', '']:
            return None
        
        # Remove extra whitespace and convert to lowercase
        text = text.strip().lower()
        
        # Patterns for different throughput formats
        patterns = [
            r'(\d+\.?\d*)\s*tps',  # "15.2 TPS"
            r'(\d+\.?\d*)\s*tokens?[/\s]s(?:ec|ond)?',  # "12 tokens/s", "12 tokens per second"
            r'(\d+\.?\d*)\s*tokens?\s+per\s+second',  # "12 tokens per second"
            r'(\d+\.?\d*)\s*t/s',  # "15.2 t/s"
            r'^(\d+\.?\d*)$',  # Just a number, assume TPS
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None

    @staticmethod
    def parse_latency(text: str) -> Optional[float]:
        """
        Parse latency value from text.
        
        Args:
            text: Text containing latency information (e.g., '0.85s', '850ms')
            
        Returns:
            Latency value in seconds, or None if parsing fails
        """
        if not text or text.strip() in ['—', '-', 'N/A', '']:
            return None
        
        # Remove extra whitespace and convert to lowercase
        text = text.strip().lower()
        
        # Patterns for different latency formats
        patterns = [
            (r'(\d+\.?\d*)\s*ms', 0.001),  # milliseconds to seconds
            (r'(\d+\.?\d*)\s*s(?:ec|onds?)?', 1.0),  # seconds
            (r'(\d+\.?\d*)\s*minutes?', 60.0),  # minutes to seconds
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1))
                    return value * multiplier
                except ValueError:
                    continue
        
        # Try to parse as just a number (assume seconds)
        try:
            return float(text)
        except ValueError:
            pass
        
        return None

    @staticmethod
    def parse_uptime(text: str) -> Optional[float]:
        """
        Parse uptime percentage from text.
        
        Args:
            text: Text containing uptime information (e.g., '99.5%', '98.2')
            
        Returns:
            Uptime percentage (0-100), or None if parsing fails
        """
        if not text or text.strip() in ['—', '-', 'N/A', '']:
            return None
        
        # Remove extra whitespace and convert to lowercase
        text = text.strip().lower()
        
        # Patterns for different uptime formats
        patterns = [
            r'(\d+\.?\d*)\s*%',  # "99.5%"
            r'^(\d+\.?\d*)$',  # Just a number, assume percentage
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    value = float(match.group(1))
                    # If value <= 1.0, it might be a decimal (0.995 -> 99.5%)
                    if 0 <= value <= 1.0:
                        return value * 100
                    # Ensure value is within valid percentage range
                    elif 0 <= value <= 100:
                        return value
                except ValueError:
                    continue
        
        return None

    @staticmethod
    def _create_provider_key(provider_data: WebProviderData) -> str:
        """
        Create a unique key for a provider offer to handle multiple offers from the same provider.
        
        Args:
            provider_data: The provider data to create a key for
            
        Returns:
            A unique string key for this provider offer
        """
        key_parts = [provider_data.provider_name]
        
        # Add distinguishing characteristics to make the key unique
        if provider_data.quantization:
            key_parts.append(f"quant:{provider_data.quantization}")
        
        if provider_data.context_window:
            key_parts.append(f"ctx:{provider_data.context_window}")
        
        if provider_data.max_completion_tokens:
            key_parts.append(f"max:{provider_data.max_completion_tokens}")
        
        return "|".join(key_parts)
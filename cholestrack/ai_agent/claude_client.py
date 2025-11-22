"""
Claude API client with data anonymization for genomic data analysis.
"""

import re
import os
import anthropic
from django.conf import settings
from typing import List, Dict, Any, Optional


class DataAnonymizer:
    """
    Anonymize sensitive patient data before sending to external AI APIs.
    """

    @staticmethod
    def anonymize_sample_id(sample_id: str) -> str:
        """
        Replace actual sample ID with anonymized version.
        Uses consistent mapping within a session.
        """
        # Generate a hash-based anonymized ID
        import hashlib
        hash_obj = hashlib.sha256(sample_id.encode())
        anon_id = f"SAMPLE_{hash_obj.hexdigest()[:8].upper()}"
        return anon_id

    @staticmethod
    def anonymize_text(text: str, sample_id_map: Dict[str, str]) -> str:
        """
        Anonymize patient identifiers in text.

        Args:
            text: Original text
            sample_id_map: Mapping of real IDs to anonymized IDs

        Returns:
            Anonymized text
        """
        anonymized = text

        # Replace sample IDs
        for real_id, anon_id in sample_id_map.items():
            anonymized = anonymized.replace(real_id, anon_id)

        # Remove common PII patterns
        # Email addresses
        anonymized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', anonymized)

        # Phone numbers (various formats)
        anonymized = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', anonymized)

        # Dates in various formats (might be birth dates)
        anonymized = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '[DATE_REDACTED]', anonymized)
        anonymized = re.sub(r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b', '[DATE_REDACTED]', anonymized)

        return anonymized

    @staticmethod
    def anonymize_variant_data(variant_data: Dict[str, Any], sample_id_map: Dict[str, str]) -> Dict[str, Any]:
        """
        Anonymize variant data dictionary.
        Removes sample IDs but keeps variant information.
        """
        anonymized = variant_data.copy()

        # Replace sample ID keys
        if 'sample_id' in anonymized:
            real_id = anonymized['sample_id']
            if real_id in sample_id_map:
                anonymized['sample_id'] = sample_id_map[real_id]

        # Keep variant data (chromosome, position, ref, alt, genes) - this is not PII
        # But remove any file paths that might contain usernames
        if 'file_path' in anonymized:
            anonymized['file_path'] = '[FILE_PATH_REDACTED]'

        return anonymized


class ClaudeAnalysisClient:
    """
    Claude API client for genomic data analysis with anonymization.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key (defaults to settings.ANTHROPIC_API_KEY)
        """
        self.api_key = api_key or getattr(settings, 'ANTHROPIC_API_KEY', None)
        if not self.api_key:
            raise ValueError("Anthropic API key not configured. Set ANTHROPIC_API_KEY in settings.")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.anonymizer = DataAnonymizer()
        self.model = getattr(settings, 'CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        sample_id_map: Optional[Dict[str, str]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Send chat completion request to Claude with anonymization.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: System prompt for the conversation
            sample_id_map: Mapping of real sample IDs to anonymized IDs
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)

        Returns:
            Response dict with 'content', 'tokens_used', etc.
        """
        sample_id_map = sample_id_map or {}

        # Anonymize messages
        anonymized_messages = []
        for msg in messages:
            anonymized_content = self.anonymizer.anonymize_text(msg['content'], sample_id_map)
            anonymized_messages.append({
                'role': msg['role'],
                'content': anonymized_content
            })

        # Anonymize system prompt
        if system_prompt:
            system_prompt = self.anonymizer.anonymize_text(system_prompt, sample_id_map)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else None,
                messages=anonymized_messages
            )

            # Extract response
            result = {
                'content': response.content[0].text if response.content else '',
                'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens,
                'model': response.model,
                'stop_reason': response.stop_reason,
            }

            return result

        except anthropic.APIError as e:
            raise Exception(f"Claude API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error calling Claude API: {str(e)}")

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the genomic analysis AI agent.
        """
        return """You are a specialized AI assistant for genomic data analysis. You help researchers and clinicians analyze variant data from whole genome/exome sequencing.

Your capabilities:
1. **Statistical Analysis**: Calculate summary statistics, variant counts, quality metrics
2. **Variant Interpretation**: Explain the significance of genetic variants
3. **Comparative Analysis**: Compare variants across samples or analysis methods
4. **Genetic Model Filtering**: Filter variants by inheritance patterns (autosomal dominant, autosomal recessive, compound heterozygous)
5. **Custom Queries**: Answer specific questions about variant data

You have access to TSV files containing variant data with columns like:
- CHROM, POS, REF, ALT: Variant location and alleles
- GENE, IMPACT, CONSEQUENCE: Functional annotation
- AF (Allele Frequency), gnomAD_AF: Population frequencies
- QUAL, DP, GQ: Quality metrics
- Genotype information (GT, AD, etc.)

Important guidelines:
- All patient data is anonymized before being sent to you
- Focus on scientific/clinical interpretation, not personal information
- When suggesting analyses, explain the approach clearly
- For complex analyses, indicate that they will be run as background jobs
- Generate reports in HTML, CSV, or Excel format as requested

When a user asks for an analysis:
1. Clarify what data files to use (which samples)
2. Explain what analysis will be performed
3. Indicate if it's a quick query or requires background processing
4. Provide clear, actionable results

Be professional, accurate, and helpful. Always prioritize data privacy and scientific rigor."""

    def analyze_variant_question(
        self,
        question: str,
        variant_data_summary: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        sample_id_map: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a question about variant data.

        Args:
            question: User's question
            variant_data_summary: Summary of available variant data
            conversation_history: Previous messages in conversation
            sample_id_map: Sample ID anonymization mapping

        Returns:
            Claude's response with analysis
        """
        messages = conversation_history or []

        # Add variant data context if provided
        if variant_data_summary:
            context_message = f"Available variant data:\n{variant_data_summary}\n\nUser question: {question}"
        else:
            context_message = question

        messages.append({
            'role': 'user',
            'content': context_message
        })

        return self.create_chat_completion(
            messages=messages,
            system_prompt=self.get_system_prompt(),
            sample_id_map=sample_id_map,
            temperature=0.7,
        )

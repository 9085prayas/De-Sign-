import os
# import hashlib
import re
from datetime import datetime
from typing import Dict, Any, List
import uuid

class AgentB:
    """Risk Assessment Agent B - Analyzes documents for risk indicators"""
    
    def __init__(self):
        self.agent_name = "Agent B - Risk Assessment"
        
        # Define risk keywords and their weights
        self.risk_keywords = {
            'high_risk': {
                'keywords': [
                    'urgent', 'critical', 'emergency', 'immediate', 'crisis',
                    'lawsuit', 'legal action', 'breach', 'violation', 'fraud',
                    'security incident', 'data leak', 'confidential leak',
                    'deadline missed', 'overdue', 'expired', 'terminated',
                    'audit finding', 'compliance issue', 'regulatory',
                    'threat', 'vulnerability', 'attack', 'compromise'
                ],
                'weight': 10
            },
            'medium_risk': {
                'keywords': [
                    'important', 'priority', 'review required', 'attention needed',
                    'pending approval', 'verification needed', 'clarification',
                    'update required', 'modification', 'change request',
                    'budget concern', 'resource issue', 'timeline concern',
                    'quality issue', 'performance issue', 'delay possible',
                    'stakeholder concern', 'client feedback', 'escalation'
                ],
                'weight': 5
            },
            'low_risk': {
                'keywords': [
                    'routine', 'standard', 'normal', 'regular', 'scheduled',
                    'informational', 'update', 'notification', 'reminder',
                    'confirmation', 'acknowledgment', 'status report',
                    'meeting minutes', 'progress report', 'monthly report',
                    'quarterly update', 'annual review', 'template',
                    'guideline', 'procedure', 'policy update'
                ],
                'weight': 1
            }
        }
        
        # Document type patterns
        self.document_types = {
            'contract': ['agreement', 'contract', 'terms', 'conditions', 'clause'],
            'financial': ['budget', 'invoice', 'payment', 'financial', 'cost', 'expense'],
            'legal': ['legal', 'law', 'regulation', 'compliance', 'audit'],
            'technical': ['specification', 'technical', 'system', 'software', 'hardware'],
            'hr': ['employee', 'staff', 'personnel', 'hr', 'human resources'],
            'general': []  # fallback
        }
    
    def analyze_file(self, file_path: str, additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze uploaded file for risk indicators
        
        Args:
            file_path: Path to the uploaded file
            additional_context: Optional context (user info, metadata, etc.)
            
        Returns:
            Dictionary containing risk assessment results
        """
        try:
            print(f"[{self.agent_name}] Starting analysis of: {os.path.basename(file_path)}")
            
            # Read and process file content
            content = self._read_file_content(file_path)
            
            if not content:
                return self._create_error_response("Unable to read file content")
            
            # Perform various analyses
            keyword_analysis = self._analyze_keywords(content)
            document_analysis = self._analyze_document_structure(content)
            content_analysis = self._analyze_content_patterns(content)
            file_analysis = self._analyze_file_metadata(file_path)
            
            # Calculate overall risk score
            risk_assessment = self._calculate_risk_level(
                keyword_analysis, 
                document_analysis, 
                content_analysis,
                file_analysis
            )
            
            # Add context if provided
            if additional_context:
                risk_assessment['context'] = additional_context
            
            # Generate final assessment
            final_assessment = self._generate_final_assessment(
                risk_assessment,
                keyword_analysis,
                document_analysis,
                content_analysis,
                file_analysis
            )
            
            print(f"[{self.agent_name}] Analysis complete - Risk Level: {final_assessment['risk_level']}")
            
            return final_assessment
            
        except Exception as e:
            print(f"[{self.agent_name}] Analysis failed: {str(e)}")
            return self._create_error_response(f"Analysis failed: {str(e)}")
    
    def _read_file_content(self, file_path: str) -> str:
        """Read file content with multiple encoding attempts"""
        encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Error reading file with {encoding}: {e}")
                continue
        
        return ""
    
    def _analyze_keywords(self, content: str) -> Dict[str, Any]:
        """Analyze content for risk-related keywords"""
        content_lower = content.lower()
        
        analysis = {
            'high_risk': {'count': 0, 'found_keywords': []},
            'medium_risk': {'count': 0, 'found_keywords': []},
            'low_risk': {'count': 0, 'found_keywords': []}
        }
        
        for risk_level, data in self.risk_keywords.items():
            for keyword in data['keywords']:
                count = content_lower.count(keyword)
                if count > 0:
                    analysis[risk_level]['count'] += count * data['weight']
                    analysis[risk_level]['found_keywords'].append({
                        'keyword': keyword,
                        'occurrences': count,
                        'weight': data['weight']
                    })
        
        return analysis
    
    def _analyze_document_structure(self, content: str) -> Dict[str, Any]:
        """Analyze document structure and characteristics"""
        lines = content.split('\n')
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        
        # Detect document type
        document_type = self._detect_document_type(content)
        
        # Analyze structure
        structure_analysis = {
            'total_lines': len(lines),
            'total_words': len(words),
            'total_sentences': len([s for s in sentences if s.strip()]),
            'average_words_per_sentence': len(words) / max(len([s for s in sentences if s.strip()]), 1),
            'document_type': document_type,
            'has_headers': self._has_headers(content),
            'has_dates': self._has_dates(content),
            'has_numbers': self._has_numbers(content),
            'has_emails': self._has_emails(content),
            'complexity_score': self._calculate_complexity(content)
        }
        
        return structure_analysis
    
    def _analyze_content_patterns(self, content: str) -> Dict[str, Any]:
        """Analyze content for specific risk patterns"""
        patterns = {
            'financial_amounts': len(re.findall(r'\$[\d,]+\.?\d*|USD\s*[\d,]+', content, re.IGNORECASE)),
            'dates_mentioned': len(re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}', content)),
            'email_addresses': len(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)),
            'phone_numbers': len(re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', content)),
            'urls': len(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)),
            'capital_words': len(re.findall(r'\b[A-Z]{2,}\b', content)),
            'exclamation_marks': content.count('!'),
            'question_marks': content.count('?')
        }
        
        return patterns
    
    def _analyze_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Analyze file metadata"""
        try:
            stat = os.stat(file_path)
            return {
                'file_size': stat.st_size,
                'file_name': os.path.basename(file_path),
                'file_extension': os.path.splitext(file_path)[1].lower(),
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            }
        except Exception as e:
            return {'error': f"Could not analyze file metadata: {str(e)}"}
    
    def _calculate_risk_level(self, keyword_analysis: Dict, document_analysis: Dict, 
                            content_analysis: Dict, file_analysis: Dict) -> Dict[str, Any]:
        """Calculate overall risk level based on all analyses"""
        
        # Base risk score from keywords
        high_risk_score = keyword_analysis['high_risk']['count']
        medium_risk_score = keyword_analysis['medium_risk']['count']
        low_risk_score = keyword_analysis['low_risk']['count']
        
        # Adjust based on document characteristics
        if document_analysis.get('document_type') in ['legal', 'financial', 'contract']:
            high_risk_score += 5
        
        # Adjust based on content patterns
        if content_analysis.get('financial_amounts', 0) > 0:
            medium_risk_score += 3
        
        if content_analysis.get('exclamation_marks', 0) > 5:
            high_risk_score += 2
        
        # Adjust based on file size (very large files might be more complex)
        file_size = file_analysis.get('file_size', 0)
        if file_size > 100000:  # > 100KB
            medium_risk_score += 1
        
        # Calculate total weighted score
        total_score = (high_risk_score * 3) + (medium_risk_score * 2) + (low_risk_score * 1)
        
        # Determine risk level and confidence
        if high_risk_score > 0 or total_score > 50:
            risk_level = "HIGH RISK"
            confidence = min(85 + high_risk_score, 95)
        elif medium_risk_score > 0 or total_score > 20:
            risk_level = "MEDIUM RISK"
            confidence = min(70 + medium_risk_score, 85)
        else:
            risk_level = "LOW RISK"
            confidence = max(50, min(60 + low_risk_score, 70))
        
        return {
            'risk_level': risk_level,
            'confidence': confidence,
            'risk_score': total_score,
            'component_scores': {
                'high_risk': high_risk_score,
                'medium_risk': medium_risk_score,
                'low_risk': low_risk_score
            }
        }
    
    def _generate_final_assessment(self, risk_assessment: Dict, keyword_analysis: Dict,
                                 document_analysis: Dict, content_analysis: Dict,
                                 file_analysis: Dict) -> Dict[str, Any]:
        """Generate final comprehensive assessment"""
        
        # Create summary
        high_indicators = len(keyword_analysis['high_risk']['found_keywords'])
        medium_indicators = len(keyword_analysis['medium_risk']['found_keywords'])
        low_indicators = len(keyword_analysis['low_risk']['found_keywords'])
        
        summary = (f"Document analyzed with {risk_assessment['confidence']}% confidence. "
                  f"Found {high_indicators} high-risk, {medium_indicators} medium-risk, "
                  f"and {low_indicators} low-risk indicators.")
        
        # Generate recommendations
        recommendations = self._get_recommendations(
            risk_assessment['risk_level'],
            keyword_analysis,
            document_analysis
        )
        
        return {
            'risk_level': risk_assessment['risk_level'],
            'confidence': risk_assessment['confidence'],
            'risk_score': risk_assessment['risk_score'],
            'summary': summary,
            'recommendations': recommendations,
            'analysis_details': {
                'keyword_analysis': keyword_analysis,
                'document_analysis': document_analysis,
                'content_analysis': content_analysis,
                'file_analysis': file_analysis,
                'component_scores': risk_assessment['component_scores']
            },
            'analysis_id': f"RISK_{uuid.uuid4().hex[:8].upper()}",
            'analyzed_at': datetime.now().isoformat(),
            'agent_version': "1.0"
        }
    
    def _detect_document_type(self, content: str) -> str:
        """Detect document type based on content"""
        content_lower = content.lower()
        
        for doc_type, keywords in self.document_types.items():
            if doc_type == 'general':
                continue
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score >= 2:  # Need at least 2 matching keywords
                return doc_type
        
        return 'general'
    
    def _has_headers(self, content: str) -> bool:
        """Check if document has header-like structures"""
        lines = content.split('\n')
        header_patterns = [
            r'^[A-Z\s]+$',  # All caps lines
            r'^\d+\.\s+[A-Z]',  # Numbered sections
            r'^[A-Z][a-z]+:',  # Title: format
        ]
        
        header_count = 0
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if any(re.match(pattern, line) for pattern in header_patterns):
                header_count += 1
        
        return header_count > 0
    
    def _has_dates(self, content: str) -> bool:
        """Check if document contains dates"""
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}-\d{2}-\d{2}',
            r'[A-Za-z]+ \d{1,2}, \d{4}'
        ]
        return any(re.search(pattern, content) for pattern in date_patterns)
    
    def _has_numbers(self, content: str) -> bool:
        """Check if document contains significant numbers"""
        return bool(re.search(r'\d+', content))
    
    def _has_emails(self, content: str) -> bool:
        """Check if document contains email addresses"""
        return bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content))
    
    def _calculate_complexity(self, content: str) -> float:
        """Calculate document complexity score"""
        words = content.split()
        if not words:
            return 0
        
        # Average word length
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Sentence complexity (words per sentence)
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        avg_sentence_length = len(words) / max(len(sentences), 1)
        
        # Unique word ratio
        unique_words = len(set(word.lower() for word in words))
        unique_ratio = unique_words / len(words)
        
        # Combine metrics (normalized to 0-100)
        complexity = (
            (min(avg_word_length, 10) / 10 * 30) +
            (min(avg_sentence_length, 30) / 30 * 40) +
            (unique_ratio * 30)
        )
        
        return round(complexity, 2)
    
    def _get_recommendations(self, risk_level: str, keyword_analysis: Dict, 
                           document_analysis: Dict) -> List[str]:
        """Get recommendations based on risk level and analysis"""
        base_recommendations = {
            'HIGH RISK': [
                'Immediate review required',
                'Consider additional approval layers',
                'Document all decisions carefully',
                'Escalate to senior management if needed'
            ],
            'MEDIUM RISK': [
                'Standard review process recommended',
                'Verify key details before proceeding',
                'Proceed with normal caution',
                'Monitor for any changes'
            ],
            'LOW RISK': [
                'Routine processing acceptable',
                'Standard documentation sufficient',
                'Regular monitoring adequate'
            ]
        }
        
        recommendations = base_recommendations.get(risk_level, ['Standard processing'])
        
        # Add specific recommendations based on analysis
        if keyword_analysis['high_risk']['found_keywords']:
            recommendations.append('Pay special attention to high-risk indicators found')
        
        if document_analysis.get('document_type') == 'legal':
            recommendations.append('Legal review recommended')
        elif document_analysis.get('document_type') == 'financial':
            recommendations.append('Financial verification recommended')
        
        return recommendations
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'error': error_message,
            'risk_level': 'UNKNOWN',
            'confidence': 0,
            'risk_score': 0,
            'summary': f'Analysis failed: {error_message}',
            'recommendations': ['Manual review required due to analysis failure'],
            'analysis_details': {},
            'analysis_id': f"ERR_{uuid.uuid4().hex[:8].upper()}",
            'analyzed_at': datetime.now().isoformat(),
            'agent_version': '1.0'
        }
    
    def validate_file_for_analysis(self, file_path: str) -> bool:
        """Validate if file can be analyzed"""
        if not os.path.exists(file_path):
            return False
        
        # Check file size (max 10MB)
        if os.path.getsize(file_path) > 10 * 1024 * 1024:
            return False
        
        # Check file extension
        allowed_extensions = ['.txt', '.doc', '.docx', '.pdf', '.md', '.rtf']
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in allowed_extensions:
            return False
        
        return True

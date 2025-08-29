# Investigation Workflows Guide

## Overview

This guide provides detailed workflows for conducting investigations using Project Dharma. It covers systematic approaches to threat detection, campaign analysis, and evidence collection for security analysts and investigators.

## Investigation Methodology

### DHARMA Investigation Framework

The DHARMA framework follows a structured approach:

**D** - Detect: Identify potential threats and anomalies
**H** - Hypothesize: Form initial theories about observed activity
**A** - Analyze: Conduct detailed analysis using available tools
**R** - Relate: Connect findings to broader patterns or known threats
**M** - Mitigate: Take appropriate response actions
**A** - Archive: Document findings and lessons learned

## Threat Detection Workflows

### 1. Routine Monitoring Workflow

#### Daily Monitoring Checklist
- [ ] Review overnight alerts and system notifications
- [ ] Check platform activity levels and anomalies
- [ ] Monitor trending topics and hashtags
- [ ] Assess sentiment distribution changes
- [ ] Review bot detection alerts
- [ ] Check for new campaign detections

#### Weekly Assessment
- [ ] Analyze weekly trends and patterns
- [ ] Review resolved investigations for lessons learned
- [ ] Update threat intelligence databases
- [ ] Assess system performance and data quality
- [ ] Conduct team briefings on emerging threats

#### Monthly Review
- [ ] Comprehensive threat landscape assessment
- [ ] Review and update investigation procedures
- [ ] Analyze system effectiveness metrics
- [ ] Update training materials and best practices
- [ ] Conduct security and compliance reviews

### 2. Alert-Driven Investigation Workflow

#### Step 1: Alert Assessment (5 minutes)
1. **Initial Triage**
   - Review alert severity and type
   - Check alert confidence scores
   - Assess potential impact and urgency
   - Determine if immediate escalation is needed

2. **Context Gathering**
   - Review related alerts and patterns
   - Check for similar historical incidents
   - Assess current threat landscape context
   - Identify potential stakeholders to notify

#### Step 2: Preliminary Analysis (15 minutes)
1. **Content Review**
   - Examine flagged content and metadata
   - Assess content authenticity and source
   - Review engagement metrics and reach
   - Check for policy violations or legal issues

2. **Actor Analysis**
   - Review account profiles and history
   - Check behavioral indicators and patterns
   - Assess account authenticity and bot probability
   - Identify potential network connections

#### Step 3: Deep Investigation (1-4 hours)
1. **Network Analysis**
   - Map account relationships and interactions
   - Identify coordination patterns and timing
   - Analyze information flow and amplification
   - Assess network structure and influence

2. **Content Analysis**
   - Perform detailed sentiment and narrative analysis
   - Check for propaganda techniques and manipulation
   - Analyze multimedia content and metadata
   - Track content evolution and variations

3. **Temporal Analysis**
   - Examine activity timing and patterns
   - Identify synchronized behaviors
   - Assess automation indicators
   - Correlate with external events

#### Step 4: Conclusion and Response (30 minutes)
1. **Findings Documentation**
   - Summarize key findings and evidence
   - Assess threat level and confidence
   - Document investigation methodology
   - Prepare executive summary

2. **Response Actions**
   - Determine appropriate response measures
   - Notify relevant stakeholders
   - Update threat intelligence databases
   - Schedule follow-up monitoring

## Campaign Investigation Workflows

### 1. Coordinated Inauthentic Behavior (CIB) Investigation

#### Phase 1: Detection and Scoping
1. **Initial Detection**
   - Review campaign detection alerts
   - Assess coordination indicators and scores
   - Identify preliminary participant accounts
   - Determine investigation priority

2. **Scope Definition**
   - Define investigation boundaries and timeline
   - Identify key research questions
   - Determine required resources and expertise
   - Set investigation milestones and deadlines

#### Phase 2: Data Collection and Analysis
1. **Participant Identification**
   ```
   Investigation Checklist:
   - [ ] Identify core participant accounts
   - [ ] Map account creation patterns
   - [ ] Analyze profile similarities
   - [ ] Check for shared infrastructure
   - [ ] Assess behavioral synchronization
   ```

2. **Content Analysis**
   ```
   Content Review Process:
   - [ ] Collect all campaign-related content
   - [ ] Analyze message templates and variations
   - [ ] Identify narrative themes and objectives
   - [ ] Track content evolution over time
   - [ ] Assess multimedia content authenticity
   ```

3. **Network Mapping**
   ```
   Network Analysis Steps:
   - [ ] Create interaction network graphs
   - [ ] Identify key influencers and amplifiers
   - [ ] Map information flow patterns
   - [ ] Analyze engagement authenticity
   - [ ] Assess network resilience and structure
   ```

#### Phase 3: Attribution and Impact Assessment
1. **Attribution Analysis**
   - Analyze technical indicators and infrastructure
   - Review operational security patterns
   - Compare with known threat actor TTPs
   - Assess geographic and temporal indicators

2. **Impact Assessment**
   - Calculate reach and engagement metrics
   - Assess narrative penetration and adoption
   - Evaluate potential real-world impact
   - Determine ongoing threat level

#### Phase 4: Reporting and Response
1. **Investigation Report**
   - Executive summary with key findings
   - Detailed technical analysis
   - Evidence documentation and preservation
   - Recommendations for response actions

2. **Response Coordination**
   - Brief relevant stakeholders
   - Coordinate with platform partners
   - Update detection systems and rules
   - Plan ongoing monitoring activities

### 2. Disinformation Campaign Analysis

#### Narrative Tracking Workflow
1. **Narrative Identification**
   - Identify core narrative themes
   - Track narrative evolution and adaptation
   - Analyze supporting evidence and claims
   - Assess narrative credibility and impact

2. **Propagation Analysis**
   - Map narrative spread across platforms
   - Identify key amplification nodes
   - Analyze timing and coordination patterns
   - Assess organic vs. artificial amplification

3. **Counter-Narrative Assessment**
   - Identify opposing narratives and responses
   - Analyze debate dynamics and engagement
   - Assess effectiveness of counter-messaging
   - Recommend response strategies

#### Multimedia Content Investigation
1. **Image and Video Analysis**
   ```
   Multimedia Investigation Checklist:
   - [ ] Reverse image/video search
   - [ ] Metadata analysis and extraction
   - [ ] Technical authenticity assessment
   - [ ] Context and provenance verification
   - [ ] Manipulation detection analysis
   ```

2. **Link and Website Analysis**
   ```
   Link Investigation Process:
   - [ ] Domain registration and ownership
   - [ ] Website content and structure analysis
   - [ ] Traffic and engagement assessment
   - [ ] Technical infrastructure analysis
   - [ ] Relationship mapping to other sites
   ```

## Bot Network Investigation

### 1. Automated Behavior Detection

#### Behavioral Analysis Workflow
1. **Activity Pattern Analysis**
   - Examine posting frequency and timing
   - Analyze content repetition and templates
   - Assess engagement patterns and authenticity
   - Check for coordinated activity timing

2. **Account Characteristics Review**
   - Profile completeness and authenticity
   - Account creation and aging patterns
   - Network connections and relationships
   - Historical activity and evolution

#### Technical Indicators Assessment
1. **Infrastructure Analysis**
   - IP address and geolocation patterns
   - Device and browser fingerprinting
   - API usage patterns and automation signs
   - Network infrastructure relationships

2. **Coordination Detection**
   - Synchronized activity identification
   - Shared content and messaging patterns
   - Cross-platform coordination assessment
   - Command and control infrastructure

### 2. Bot Network Mapping

#### Network Discovery Process
1. **Seed Account Identification**
   - Start with high-confidence bot accounts
   - Identify accounts with similar characteristics
   - Use clustering algorithms for grouping
   - Validate findings with manual review

2. **Network Expansion**
   - Follow interaction patterns and connections
   - Identify additional network participants
   - Map hierarchical relationships
   - Assess network boundaries and scope

3. **Network Analysis**
   - Calculate network metrics and centrality
   - Identify key nodes and controllers
   - Assess network resilience and structure
   - Predict network behavior and evolution

## Evidence Collection and Preservation

### 1. Digital Evidence Standards

#### Evidence Collection Protocol
1. **Content Preservation**
   ```
   Evidence Collection Checklist:
   - [ ] Screenshot capture with metadata
   - [ ] Raw data export and backup
   - [ ] URL and link preservation
   - [ ] Timestamp and source documentation
   - [ ] Chain of custody documentation
   ```

2. **Metadata Preservation**
   - Complete technical metadata capture
   - Platform-specific data elements
   - User interaction and engagement data
   - Network and infrastructure information

#### Evidence Validation
1. **Authenticity Verification**
   - Cross-platform content verification
   - Technical metadata validation
   - Source credibility assessment
   - Independent confirmation when possible

2. **Integrity Maintenance**
   - Cryptographic hashing for integrity
   - Secure storage and access controls
   - Audit trail maintenance
   - Regular integrity verification

### 2. Investigation Documentation

#### Investigation File Structure
```
Investigation_YYYY-MM-DD_CaseName/
├── 01_Initial_Assessment/
│   ├── alert_details.pdf
│   ├── initial_findings.md
│   └── scope_definition.md
├── 02_Data_Collection/
│   ├── raw_data/
│   ├── screenshots/
│   └── metadata/
├── 03_Analysis/
│   ├── network_analysis/
│   ├── content_analysis/
│   └── temporal_analysis/
├── 04_Evidence/
│   ├── preserved_content/
│   ├── technical_indicators/
│   └── validation_data/
└── 05_Reporting/
    ├── executive_summary.pdf
    ├── technical_report.md
    └── recommendations.md
```

#### Documentation Standards
1. **Investigation Notes**
   - Chronological activity log
   - Decision rationale documentation
   - Methodology and tool usage notes
   - Collaboration and communication records

2. **Analysis Documentation**
   - Detailed analytical findings
   - Statistical analysis and metrics
   - Visual analysis and charts
   - Confidence assessments and limitations

## Quality Assurance and Validation

### 1. Peer Review Process

#### Investigation Review Checklist
- [ ] Methodology appropriateness and rigor
- [ ] Evidence quality and authenticity
- [ ] Analysis accuracy and completeness
- [ ] Conclusion validity and confidence
- [ ] Documentation completeness and clarity

#### Review Stages
1. **Initial Review** (24 hours)
   - Methodology and approach validation
   - Evidence collection assessment
   - Initial findings review

2. **Detailed Review** (48 hours)
   - Comprehensive analysis validation
   - Statistical and technical review
   - Alternative hypothesis consideration

3. **Final Review** (24 hours)
   - Report accuracy and completeness
   - Recommendation appropriateness
   - Executive summary validation

### 2. Continuous Improvement

#### Lessons Learned Process
1. **Post-Investigation Review**
   - Methodology effectiveness assessment
   - Tool and technique evaluation
   - Time and resource utilization review
   - Outcome and impact assessment

2. **Process Improvement**
   - Workflow optimization opportunities
   - Tool and capability enhancement needs
   - Training and skill development requirements
   - Policy and procedure updates

#### Knowledge Management
1. **Case Study Development**
   - Anonymized case documentation
   - Best practice identification
   - Training material creation
   - Methodology refinement

2. **Threat Intelligence Integration**
   - IOC and TTPs documentation
   - Threat actor profiling updates
   - Detection rule enhancement
   - Intelligence sharing preparation

## Emergency Response Procedures

### 1. Critical Threat Response

#### Immediate Response (0-15 minutes)
1. **Threat Assessment**
   - Assess immediate threat level and impact
   - Determine if escalation is required
   - Identify affected systems and stakeholders
   - Activate appropriate response procedures

2. **Initial Containment**
   - Implement immediate protective measures
   - Notify key stakeholders and authorities
   - Begin evidence preservation activities
   - Establish incident command structure

#### Short-term Response (15 minutes - 4 hours)
1. **Detailed Investigation**
   - Conduct rapid but thorough analysis
   - Gather additional evidence and context
   - Assess ongoing threat and evolution
   - Coordinate with external partners

2. **Response Actions**
   - Implement appropriate countermeasures
   - Coordinate with platform partners
   - Brief senior leadership and stakeholders
   - Monitor for threat evolution

#### Long-term Response (4+ hours)
1. **Comprehensive Analysis**
   - Complete detailed investigation
   - Prepare comprehensive threat assessment
   - Develop long-term mitigation strategies
   - Document lessons learned

2. **Recovery and Improvement**
   - Implement system improvements
   - Update detection and response procedures
   - Conduct post-incident review
   - Share intelligence with partners

### 2. Coordination Procedures

#### Internal Coordination
- **Incident Commander**: Overall response coordination
- **Technical Lead**: Investigation and analysis coordination
- **Communications Lead**: Stakeholder and media coordination
- **Legal Counsel**: Legal and compliance guidance

#### External Coordination
- **Government Partners**: Intelligence and law enforcement
- **Platform Partners**: Content and account actions
- **Industry Partners**: Threat intelligence sharing
- **Academic Partners**: Research and analysis support

This investigation workflows guide provides systematic approaches to threat detection and analysis. Regular training and practice with these workflows ensures effective and consistent investigation capabilities.
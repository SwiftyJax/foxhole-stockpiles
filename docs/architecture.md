# Architecture Documentation

## Overview

Foxhole Stockpiles is a computer vision and OCR system designed to extract structured data from game screenshots. The architecture follows a modular design with clear separation of concerns, enabling both CLI and API usage patterns.

## System Architecture

### High-Level Components

**Entry Points** → **Service Layer** → **External Dependencies/Outputs**

**1. Entry Points:**
- CLI Tools (`fs scanner`, `fs server`, etc.)
- FastAPI Server (HTTP API)
- Docker Container (production deployment)

**2. Service Layer:**
- **OCRCoordinator:** Orchestrates the entire detection and recognition pipeline
- **StockpileDetector:** Detects quantity boxes and icon positions in screenshots
- **TemplateManager:** Loads and manages template database for icon matching
- **TextExtractor:** OCR processing for quantity recognition
- **OutputHandler:** Formats results for different output targets

**3. External Dependencies:**
- OpenCV: Image processing and template matching
- NumPy: Numerical operations and array handling
- Tesseract OCR: Text recognition from quantity boxes

**4. Output Targets:**
- Console output (CLI)
- JSON files
- Webhooks (HTTP POST to external services)

### Data Flow

```
Screenshot Image
    ↓
[StockpileDetector] → Detect boxes and extract regions
    ↓
[TemplateManager] → Match icons using NCC + pHash
    ↓
[TextExtractor] → OCR for quantities
    ↓
[OutputHandler] → Format and send results
    ↓
Output (JSON/Console/Webhook)
```

## Core Design Decisions

### 1. Multi-Stage Processing Pipeline

**Decision:** Split image processing into distinct stages (detection → matching → recognition → output)

**Rationale:**
- **Maintainability:** Each stage can be tested and debugged independently
- **Performance:** Stages can be optimized separately
- **Flexibility:** Easy to swap algorithms or add preprocessing steps
- **Debugging:** Inspector tool can examine output at each stage

**Trade-offs:**
- More complex coordination logic in `OCRCoordinator`
- Slight memory overhead passing data between stages

### 2. Template-Based Icon Recognition

**Decision:** Pre-generated template database with resolution-specific variants

**Rationale:**
- **Accuracy:** Precise matching with NCC (Normalized Cross-Correlation)
- **Speed:** Pre-computed templates and pHash filtering avoid expensive computation
- **Flexibility:** Easy to add new items by updating template database
- **Multi-resolution:** Supports different screen resolutions without retraining

**Implementation:**
```python
# Template database structure
{
    resolution: {
        templates: [
            IconTemplate(
                image=np.ndarray,      # Pre-scaled image
                phash=int,            # Fast similarity filter
                crated=bool,          # Crate overlay applied
                code=str,             # Item code
                faction=ItemFaction,  # Item faction
                category=ItemCategory,# Item category
                mod=str,              # Mod name
                resolution=SupportedResolution
            ),
            ...
        ]
    }
}
```

**Trade-offs:**
- Database size grows with resolutions and item count (~5-10MB)
- Requires regeneration when game assets change
- Less flexible than ML-based approaches for new items

### 3. Two-Phase Icon Matching

**Decision:** pHash filtering followed by NCC matching

**Rationale:**
- **Performance:** pHash eliminates 90%+ of candidates in <1ms
- **Accuracy:** NCC provides precise confidence scores
- **Early Exit:** Can stop at high-confidence matches (0.95+)

**Algorithm:**
```python
def match_icon(detected_icon):
    # Phase 1: Fast filtering
    candidates = phash_filter(detected_icon, threshold=12)
    # Reduces 1426 templates to ~25 candidates

    # Phase 2: Precise matching
    for candidate in sorted_by_phash_similarity(candidates):
        confidence = ncc_match(detected_icon, candidate.template)
        if confidence > early_exit_threshold and early_exit_threshold > 0:  # Early exit
            return candidate, confidence

    return best_match, best_confidence
```

**Performance:**
- Without pHash: ~1.5s per icon (1426 NCC operations)
- With pHash: ~50ms per icon (25 NCC operations)
- 30x speedup

### 4. Custom Tesseract Model for Quantity Detection

**Decision:** Train custom model for Foxhole's Renner font

**Rationale:**
- **Character Confusion:** Default Tesseract misreads similar characters (1 vs 7, 0 vs O)
- **Font-Specific:** Renner font has unique character shapes not well-represented in generic models
- **Accuracy:** Custom model trained specifically on quantity box samples
- **Reduced Character Set:** Only digits needed, improving recognition speed

**Training Data:**
- 100+ manually labeled quantity boxes
- Multiple gamma/brightness variations
- Different background colors
- Focus on problematic characters (1, 7, 0)

**Results:**
- Generic Tesseract: ~70% accuracy (frequent 1/7 and 0/O confusion)
- Custom model: ~95% accuracy

### 5. Pydantic v2 for Data Validation

**Decision:** Use Pydantic for all data models and configuration

**Rationale:**
- **Type Safety:** Runtime validation catches errors early
- **Documentation:** Models serve as API documentation
- **Configuration:** Settings validation with environment variables
- **Performance:** Pydantic v2 is Rust-based and very fast

**Example:**
```python
class ScannerSettings(BaseModel):
    database_path: Path
    early_exit_threshold: float = Field(ge=0.0, le=1.0, default=0.0)

    @field_validator("database_path")
    def validate_database_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"Database not found: {v}")
        return v
```

### 6. Multi-Pattern Entry Points

**Decision:** Support CLI, API, and Docker deployments

**Rationale:**
- **CLI:** Interactive development and debugging
- **API:** Integration with web applications
- **Docker:** Production deployment with isolation

**Implementation Strategy:**
- Shared core services (`OCRCoordinator`)
- Thin adapters for each entry point
- No business logic in entry points

### 7. Dependency Injection via Settings

**Decision:** Use `pydantic-settings` for configuration management

**Rationale:**
- **12-Factor App:** Environment-based configuration
- **Testing:** Easy to override settings in tests
- **Documentation:** Settings schema serves as config docs
- **Validation:** Type checking and validation built-in

**Configuration Hierarchy:**
```
1. Environment variables (FS_*)
2. .env file
3. Default values in code
```

## Scalability Considerations

### Current Performance

- **Processing Time:** 1-3 seconds per 4K screenshot
- **Memory Usage:** ~300MB per worker process
- **Concurrency:** Stateless design allows horizontal scaling

### Bottlenecks

1. **Template Matching:** O(n) with number of templates
   - **Mitigation:** pHash pre-filtering reduces effective n by 97%

2. **Tesseract OCR:** ~100ms per quantity box
   - **Mitigation:** Parallel processing across icon groups

3. **Image Decoding:** Large screenshots (4K+)
   - **Mitigation:** OpenCV's efficient imread

### Horizontal Scaling

**API Server:**
```yaml
# Docker Compose scaling
docker-compose up -d --scale api=4
```

**Design Features:**
- Stateless request handling
- No shared mutable state
- Read-only database access
- Independent worker processes

**Estimated Capacity:**
- Single worker: ~30 requests/minute
- 4 workers: ~120 requests/minute

### Potential Optimizations

1. **GPU Acceleration:** OpenCV CUDA for template matching
2. **Caching:** Cache frequent template matches
3. **Preprocessing Pipeline:** Parallel preprocessing of image regions
4. **Database Optimization:** Memory-mapped database files

## Technology Choices

### Why Template Matching Over Machine Learning?

**Background:** An earlier version of this project used Keras/TensorFlow for object detection.

**Decision:** Switched to template matching approach

**Key Difference:**

| Aspect | ML Version | Template Matching |
|--------|-----------|-------------------|
| Executable Size | 1 GB | 65-100 MB |

**Rationale:**
The 10-15x size reduction was critical for enabling users to embed this tool in their own scripts and workflows without requiring ML dependencies or large model files.

## Error Handling Strategy

### Layered Error Handling

1. **Input Validation:** Pydantic catches invalid data
2. **Business Logic:** Service layer raises domain exceptions
3. **Entry Points:** Convert exceptions to appropriate responses
   - CLI: Exit codes and error messages
   - API: HTTP status codes and JSON errors

### Graceful Degradation

- Unknown icons → Mark as "Unknown" but continue processing (quantity still extracted via OCR)
- Missing database → Clear error message with resolution steps

## Summary

The architecture follows a modular design with clear separation between:
- Entry points (CLI, API, Docker)
- Service layer (detection, matching, OCR)
- External dependencies (OpenCV, Tesseract)

Key technical decisions:
- Template matching over ML (size and portability)
- Two-phase icon matching (pHash + NCC)
- Custom Tesseract model (font-specific accuracy)
- Pydantic for validation (type safety)

# 2. Architecture Decision Record: Restructure Discord Bot Project Architecture

## Status
Accepted

## Context
The current project structure organizes code by technical layers (cogs, data, models, services, utils). While this structure initially made sense, it has become increasingly difficult to maintain and navigate as the project grows. The current issues include:

1. Related code is scattered across multiple directories based on type rather than functionality
2. Dependencies between components are not clearly visible
3. Adding new features requires touching multiple directories
4. Understanding the full scope of a feature requires looking through multiple directories
5. Risk of creating circular dependencies between layers
6. Difficult to implement feature-level testing

## Decision
We will restructure the project to use a feature-based architecture instead of a layer-based architecture. The new structure will:

1. Organize code primarily by feature/domain
2. Maintain a core module for essential bot functionality
3. Create a shared module for truly cross-cutting concerns
4. Group all feature-related code (models, services, repositories) in feature-specific directories

### New Structure
```
kusogaki_bot/
├── core/
│   ├── db.py
│   ├── bot.py
│   ├── exceptions.py
│   └── base_cog.py
├── features/
│   ├── food_tracking/
│   ├── quiz/
│   ├── reminders/
│   ├── threads/
│   └── polls/
├── shared/
│   ├── models/
│   ├── services/
│   └── utils/
└── main.py
```

### Key Changes
1. Move from layer-based to feature-based organization
2. Each feature directory contains all related components (cog, models, service, repository)
3. Introduce clear dependency hierarchy: features → core → shared
4. Centralize cross-cutting concerns in shared module
5. Move base functionality to core module

## Consequences

### Positive
1. **Improved Maintainability**
   - Related code is co-located
   - Features can be modified independently
   - Clear boundaries between features
   - Easier to understand feature scope

2. **Better Scalability**
   - New features can be added without modifying existing code
   - Clear template for feature implementation
   - Reduced risk of dependency cycles

3. **Enhanced Developer Experience**
   - More intuitive code navigation
   - Clearer import paths
   - Easier to onboard new developers
   - Better support for feature-based testing

4. **Clearer Dependencies**
   - Explicit dependency hierarchy
   - Reduced coupling between features
   - Easier to manage shared code

### Negative
1. **Migration Effort**
   - Requires significant refactoring of existing code
   - Need to update import statements throughout the codebase

2. **Learning Curve**
   - Team needs to adapt to new structure
   - Initial overhead in understanding new organization

3. **Potential Challenges**
   - Need to carefully identify truly shared code
   - Risk of code duplication if shared code isn't properly identified
   - Need to establish clear guidelines for when to create new features vs. extending existing ones

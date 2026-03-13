/**
 * A2UI WebApp Renderer
 * Parses A2UI JSON and renders to HTML components
 */

class A2UIRenderer {
    constructor(container) {
        this.container = container;
        this.components = new Map();
        this.dataModel = {};
        this.rootComponentId = null;
        this.telegram = window.Telegram?.WebApp;
        this.sessionId = null;
        this.apiBaseUrl = '';
        
        // Initialize Telegram WebApp if available
        if (this.telegram) {
            this.telegram.ready();
            this.telegram.expand();
            
            // Get initData for session identification
            const initData = this.telegram.initDataUnsafe;
            if (initData && initData.user) {
                this.sessionId = `tg_${initData.user.id}_${Date.now()}`;
            }
        }
        
        // Load saved state if available
        this.loadState();
    }

    /**
     * Load saved state from backend
     */
    async loadState() {
        if (!this.sessionId || !this.apiBaseUrl) return;
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/state/${this.sessionId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.state) {
                    this.dataModel = { ...this.dataModel, ...data.state };
                    // Re-render if we have a root component
                    if (this.rootComponentId) {
                        this.container.innerHTML = '';
                        this.renderComponent(this.rootComponentId);
                    }
                }
            }
        } catch (e) {
            console.warn('Failed to load state:', e);
        }
    }

    /**
     * Save state to backend
     */
    async saveState() {
        if (!this.sessionId || !this.apiBaseUrl) return;
        
        try {
            await fetch(`${this.apiBaseUrl}/state/${this.sessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: this.dataModel })
            });
        } catch (e) {
            console.warn('Failed to save state:', e);
        }
    }

    /**
     * Main render method
     * @param {Object} payload - A2UI payload
     */
    render(payload) {
        this.container.innerHTML = '';
        
        if (!payload) {
            this.showError('No payload provided');
            return;
        }

        // Handle different message types
        const msgType = payload.type || 'beginRendering';
        
        switch (msgType) {
            case 'beginRendering':
                this.handleBeginRendering(payload);
                break;
            case 'surfaceUpdate':
                this.handleSurfaceUpdate(payload);
                break;
            case 'dataModelUpdate':
                this.handleDataModelUpdate(payload);
                break;
            default:
                // Try to render as direct component
                this.renderDirect(payload);
        }
    }

    /**
     * Handle beginRendering message
     */
    handleBeginRendering(message) {
        this.components.clear();
        this.dataModel = message.dataModel || {};
        this.rootComponentId = message.rootComponentId;
        
        // Register all components
        if (message.components) {
            message.components.forEach(comp => {
                this.registerComponent(comp);
            });
        }
        
        // Render root component
        if (this.rootComponentId) {
            this.renderComponent(this.rootComponentId);
        }
    }

    /**
     * Handle surfaceUpdate message
     */
    handleSurfaceUpdate(message) {
        // Update data model
        if (message.dataModel) {
            this.mergeDataModel(message.dataModel);
        }
        
        // Update components
        if (message.components) {
            message.components.forEach(comp => {
                this.registerComponent(comp);
            });
        }
        
        // Remove components
        if (message.removedComponents) {
            message.removedComponents.forEach(id => {
                this.components.delete(id);
            });
        }
        
        // Re-render specified components
        const targetIds = message.updateComponentIds || [this.rootComponentId];
        if (targetIds.length === 1 && targetIds[0] === this.rootComponentId) {
            this.container.innerHTML = '';
            this.renderComponent(this.rootComponentId);
        } else {
            targetIds.forEach(id => {
                if (id) this.updateComponent(id);
            });
        }
    }

    /**
     * Handle dataModelUpdate message
     */
    handleDataModelUpdate(message) {
        if (message.dataModel) {
            this.mergeDataModel(message.dataModel);
        }
    }

    /**
     * Register a component definition
     */
    registerComponent(compDef) {
        if (compDef.id && compDef.type) {
            this.components.set(compDef.id, compDef);
        }
    }

    /**
     * Merge data model updates
     */
    mergeDataModel(updates) {
        this.deepMerge(this.dataModel, updates);
        this.saveState();
    }

    /**
     * Deep merge objects
     */
    deepMerge(target, source) {
        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                if (!target[key] || typeof target[key] !== 'object') {
                    target[key] = {};
                }
                this.deepMerge(target[key], source[key]);
            } else {
                target[key] = source[key];
            }
        }
    }

    /**
     * Render a component by ID
     */
    renderComponent(componentId) {
        const component = this.components.get(componentId);
        if (!component) {
            console.warn(`Component ${componentId} not found`);
            return;
        }
        
        const element = this.createComponentElement(component);
        if (element) {
            this.container.appendChild(element);
        }
    }

    /**
     * Update a specific component
     */
    updateComponent(componentId) {
        const existing = this.container.querySelector(`[data-component-id="${componentId}"]`);
        if (existing) {
            const component = this.components.get(componentId);
            if (component) {
                const newElement = this.createComponentElement(component);
                if (newElement) {
                    existing.replaceWith(newElement);
                }
            }
        }
    }

    /**
     * Create HTML element for a component
     */
    createComponentElement(component) {
        const { type, id, properties = {} } = component;
        
        switch (type) {
            case 'Text':
                return this.createTextComponent(id, properties);
            case 'Button':
                return this.createButtonComponent(id, properties);
            case 'Row':
                return this.createRowComponent(id, properties);
            case 'Column':
                return this.createColumnComponent(id, properties);
            case 'Card':
                return this.createCardComponent(id, properties);
            case 'TextField':
                return this.createTextFieldComponent(id, properties);
            case 'CheckBox':
                return this.createCheckBoxComponent(id, properties);
            case 'Slider':
                return this.createSliderComponent(id, properties);
            case 'List':
                return this.createListComponent(id, properties);
            case 'Image':
                return this.createImageComponent(id, properties);
            case 'Form':
                return this.createFormComponent(id, properties);
            case 'ProductCard':
                return this.createProductCardComponent(id, properties);
            case 'FileUpload':
                return this.createFileUploadComponent(id, properties);
            case 'DatePicker':
                return this.createDatePickerComponent(id, properties);
            case 'TextArea':
                return this.createTextAreaComponent(id, properties);
            default:
                console.warn(`Unknown component type: ${type}`);
                return null;
        }
    }

    /**
     * Resolve a value from properties (literal or path)
     */
    resolveValue(valueSpec) {
        if (!valueSpec) return null;
        
        if (typeof valueSpec === 'object') {
            if (valueSpec.literalString !== undefined) {
                return valueSpec.literalString;
            }
            if (valueSpec.path) {
                return this.getPathValue(valueSpec.path);
            }
        }
        return valueSpec;
    }

    /**
     * Get value from data model by path
     */
    getPathValue(path) {
        if (path.startsWith('/')) {
            path = path.slice(1);
        }
        const keys = path.split('/');
        let value = this.dataModel;
        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                return null;
            }
        }
        return value;
    }

    /**
     * Set value in data model by path
     */
    setPathValue(path, value) {
        if (path.startsWith('/')) {
            path = path.slice(1);
        }
        const keys = path.split('/');
        let target = this.dataModel;
        for (let i = 0; i < keys.length - 1; i++) {
            if (!(keys[i] in target)) {
                target[keys[i]] = {};
            }
            target = target[keys[i]];
        }
        target[keys[keys.length - 1]] = value;
        this.saveState();
    }

    /**
     * Send data back to Telegram bot
     */
    sendData(data) {
        if (this.telegram) {
            this.telegram.sendData(JSON.stringify(data));
        }
    }

    /**
     * Close WebApp
     */
    close() {
        if (this.telegram) {
            this.telegram.close();
        }
    }

    // ==================== Component Creators ====================

    /**
     * Text component
     */
    createTextComponent(id, properties) {
        const text = this.resolveValue(properties.text) || '';
        const usageHint = properties.usageHint || 'body';
        
        const element = document.createElement('div');
        element.className = `a2ui-text ${usageHint}`;
        element.dataset.componentId = id;
        element.textContent = text;
        
        return element;
    }

    /**
     * Button component
     */
    createButtonComponent(id, properties) {
        const text = this.resolveValue(properties.text) || 'Button';
        const action = properties.action || 'click';
        const variant = properties.variant || 'primary';
        const url = properties.url;
        
        const button = document.createElement('button');
        button.className = `a2ui-button ${variant}`;
        button.dataset.componentId = id;
        button.textContent = text;
        
        button.addEventListener('click', () => {
            if (url) {
                // Open URL - in Telegram WebApp use Telegram.WebApp.openLink
                if (this.telegram && this.telegram.openLink) {
                    this.telegram.openLink(url);
                } else {
                    window.open(url, '_blank');
                }
            } else {
                this.handleAction(action, id);
            }
        });
        
        return button;
    }

    /**
     * Row component - horizontal layout
     */
    createRowComponent(id, properties) {
        const row = document.createElement('div');
        row.className = 'a2ui-row';
        row.dataset.componentId = id;
        
        const children = this.getChildren(properties);
        children.forEach(child => {
            const childEl = this.createComponentElement(child);
            if (childEl) {
                row.appendChild(childEl);
            }
        });
        
        return row;
    }

    /**
     * Column component - vertical layout
     */
    createColumnComponent(id, properties) {
        const column = document.createElement('div');
        column.className = 'a2ui-column';
        column.dataset.componentId = id;
        
        const children = this.getChildren(properties);
        children.forEach(child => {
            const childEl = this.createComponentElement(child);
            if (childEl) {
                column.appendChild(childEl);
            }
        });
        
        return column;
    }

    /**
     * Card component
     */
    createCardComponent(id, properties) {
        const card = document.createElement('div');
        card.className = 'a2ui-card';
        card.dataset.componentId = id;
        
        const header = this.resolveValue(properties.header);
        if (header) {
            const headerEl = document.createElement('div');
            headerEl.className = 'a2ui-card-header';
            headerEl.textContent = header;
            card.appendChild(headerEl);
        }
        
        const children = this.getChildren(properties);
        children.forEach(child => {
            const childEl = this.createComponentElement(child);
            if (childEl) {
                card.appendChild(childEl);
            }
        });
        
        return card;
    }

    /**
     * TextField component
     */
    createTextFieldComponent(id, properties) {
        const label = this.resolveValue(properties.label) || '';
        const placeholder = this.resolveValue(properties.placeholder) || '';
        const valuePath = properties.value?.path;
        const value = valuePath ? this.getPathValue(valuePath) : '';
        const inputType = properties.inputType || 'text';
        
        const group = document.createElement('div');
        group.className = 'a2ui-form-group';
        group.dataset.componentId = id;
        
        if (label) {
            const labelEl = document.createElement('label');
            labelEl.className = 'a2ui-form-label';
            labelEl.textContent = label;
            group.appendChild(labelEl);
        }
        
        const input = document.createElement('input');
        input.className = 'a2ui-form-input';
        input.type = inputType;
        input.placeholder = placeholder;
        input.value = value || '';
        
        input.addEventListener('input', (e) => {
            if (valuePath) {
                this.setPathValue(valuePath, e.target.value);
            }
        });
        
        group.appendChild(input);
        return group;
    }

    /**
     * CheckBox component
     */
    createCheckBoxComponent(id, properties) {
        const label = this.resolveValue(properties.label) || '';
        const valuePath = properties.checked?.path;
        const checked = valuePath ? this.getPathValue(valuePath) : properties.checked || false;
        
        const container = document.createElement('div');
        container.className = `a2ui-checkbox ${checked ? 'checked' : ''}`;
        container.dataset.componentId = id;
        
        const box = document.createElement('div');
        box.className = 'a2ui-checkbox-box';
        
        const checkmark = document.createElement('span');
        checkmark.className = 'a2ui-checkbox-checkmark';
        checkmark.textContent = '✓';
        box.appendChild(checkmark);
        
        const labelEl = document.createElement('span');
        labelEl.className = 'a2ui-checkbox-label';
        labelEl.textContent = label;
        
        container.appendChild(box);
        container.appendChild(labelEl);
        
        container.addEventListener('click', () => {
            const newChecked = !container.classList.contains('checked');
            container.classList.toggle('checked', newChecked);
            if (valuePath) {
                this.setPathValue(valuePath, newChecked);
            }
        });
        
        return container;
    }

    /**
     * Slider component
     */
    createSliderComponent(id, properties) {
        const label = this.resolveValue(properties.label) || '';
        const min = properties.min || 0;
        const max = properties.max || 100;
        const step = properties.step || 1;
        const valuePath = properties.value?.path;
        const value = valuePath ? (this.getPathValue(valuePath) || min) : min;
        
        const container = document.createElement('div');
        container.className = 'a2ui-slider';
        container.dataset.componentId = id;
        
        const labelRow = document.createElement('div');
        labelRow.className = 'a2ui-slider-label';
        
        const labelEl = document.createElement('span');
        labelEl.textContent = label;
        
        const valueEl = document.createElement('span');
        valueEl.textContent = value;
        
        labelRow.appendChild(labelEl);
        labelRow.appendChild(valueEl);
        container.appendChild(labelRow);
        
        const input = document.createElement('input');
        input.className = 'a2ui-slider-input';
        input.type = 'range';
        input.min = min;
        input.max = max;
        input.step = step;
        input.value = value;
        
        input.addEventListener('input', (e) => {
            valueEl.textContent = e.target.value;
            if (valuePath) {
                this.setPathValue(valuePath, parseFloat(e.target.value));
            }
        });
        
        container.appendChild(input);
        return container;
    }

    /**
     * List component
     */
    createListComponent(id, properties) {
        const items = this.resolveListItems(properties);
        const pageSize = properties.pageSize || 5;
        const currentPage = properties.currentPage || 0;
        
        const container = document.createElement('div');
        container.className = 'a2ui-list';
        container.dataset.componentId = id;
        
        const header = this.resolveValue(properties.header);
        if (header) {
            const headerEl = document.createElement('div');
            headerEl.className = 'a2ui-list-header';
            headerEl.textContent = header;
            container.appendChild(headerEl);
        }
        
        const itemsContainer = document.createElement('div');
        itemsContainer.className = 'a2ui-list-items';
        
        const startIdx = currentPage * pageSize;
        const endIdx = Math.min(startIdx + pageSize, items.length);
        const pageItems = items.slice(startIdx, endIdx);
        
        pageItems.forEach((item, idx) => {
            const itemEl = document.createElement('div');
            itemEl.className = 'a2ui-list-item';
            itemEl.textContent = typeof item === 'string' ? item : item.label || item.name || JSON.stringify(item);
            itemEl.addEventListener('click', () => {
                this.handleAction('select', id, { index: startIdx + idx, item });
            });
            itemsContainer.appendChild(itemEl);
        });
        
        container.appendChild(itemsContainer);
        
        // Pagination
        const totalPages = Math.ceil(items.length / pageSize);
        if (totalPages > 1) {
            const pagination = document.createElement('div');
            pagination.className = 'a2ui-list-pagination';
            
            if (currentPage > 0) {
                const prevBtn = document.createElement('button');
                prevBtn.className = 'a2ui-button secondary';
                prevBtn.textContent = '← Prev';
                prevBtn.addEventListener('click', () => {
                    this.handleAction('page', id, { page: currentPage - 1 });
                });
                pagination.appendChild(prevBtn);
            }
            
            const pageInfo = document.createElement('span');
            pageInfo.textContent = `${currentPage + 1} / ${totalPages}`;
            pagination.appendChild(pageInfo);
            
            if (currentPage < totalPages - 1) {
                const nextBtn = document.createElement('button');
                nextBtn.className = 'a2ui-button secondary';
                nextBtn.textContent = 'Next →';
                nextBtn.addEventListener('click', () => {
                    this.handleAction('page', id, { page: currentPage + 1 });
                });
                pagination.appendChild(nextBtn);
            }
            
            container.appendChild(pagination);
        }
        
        return container;
    }

    /**
     * Image component
     */
    createImageComponent(id, properties) {
        const url = this.resolveValue(properties.url);
        const alt = this.resolveValue(properties.alt) || '';
        
        if (!url) {
            return null;
        }
        
        const container = document.createElement('div');
        container.className = 'a2ui-image';
        container.dataset.componentId = id;
        
        const img = document.createElement('img');
        img.src = url;
        img.alt = alt;
        
        container.appendChild(img);
        return container;
    }

    /**
     * Form component with submit
     */
    createFormComponent(id, properties) {
        const form = document.createElement('form');
        form.className = 'a2ui-form';
        form.dataset.componentId = id;
        
        const children = this.getChildren(properties);
        children.forEach(child => {
            const childEl = this.createComponentElement(child);
            if (childEl) {
                form.appendChild(childEl);
            }
        });
        
        // Submit button
        const submitText = this.resolveValue(properties.submitText) || 'Submit';
        const submitBtn = document.createElement('button');
        submitBtn.className = 'a2ui-button';
        submitBtn.type = 'submit';
        submitBtn.textContent = submitText;
        
        const submitSection = document.createElement('div');
        submitSection.className = 'a2ui-submit-section';
        submitSection.appendChild(submitBtn);
        form.appendChild(submitSection);
        
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleAction('submit', id, this.dataModel);
        });
        
        return form;
    }

    /**
     * Product Card component (specialized)
     */
    createProductCardComponent(id, properties) {
        const name = this.resolveValue(properties.name) || 'Product';
        const price = this.resolveValue(properties.price) || '';
        const description = this.resolveValue(properties.description) || '';
        const imageUrl = this.resolveValue(properties.imageUrl);
        
        const card = document.createElement('div');
        card.className = 'a2ui-product-card';
        card.dataset.componentId = id;
        
        if (imageUrl) {
            const img = document.createElement('img');
            img.className = 'a2ui-product-image';
            img.src = imageUrl;
            img.alt = name;
            card.appendChild(img);
        }
        
        const info = document.createElement('div');
        info.className = 'a2ui-product-info';
        
        const titleEl = document.createElement('div');
        titleEl.className = 'a2ui-product-title';
        titleEl.textContent = name;
        info.appendChild(titleEl);
        
        if (price) {
            const priceEl = document.createElement('div');
            priceEl.className = 'a2ui-product-price';
            priceEl.textContent = price;
            info.appendChild(priceEl);
        }
        
        if (description) {
            const descEl = document.createElement('div');
            descEl.className = 'a2ui-product-description';
            descEl.textContent = description;
            info.appendChild(descEl);
        }
        
        const actions = document.createElement('div');
        actions.className = 'a2ui-product-actions';
        
        const buyBtn = document.createElement('button');
        buyBtn.className = 'a2ui-button';
        buyBtn.textContent = 'Buy Now';
        buyBtn.addEventListener('click', () => {
            this.handleAction('buy', id, { product: name, price });
        });
        
        const detailsBtn = document.createElement('button');
        detailsBtn.className = 'a2ui-button secondary';
        detailsBtn.textContent = 'Details';
        detailsBtn.addEventListener('click', () => {
            this.handleAction('details', id);
        });
        
        actions.appendChild(buyBtn);
        actions.appendChild(detailsBtn);
        info.appendChild(actions);
        
        card.appendChild(info);
        return card;
    }

    /**
     * File Upload component
     */
    createFileUploadComponent(id, properties) {
        const label = this.resolveValue(properties.label) || 'Upload File';
        const accept = properties.accept || '*/*';
        const multiple = properties.multiple || false;
        const maxSize = properties.maxSize || 10 * 1024 * 1024; // 10MB default
        
        const container = document.createElement('div');
        container.className = 'a2ui-form-group';
        container.dataset.componentId = id;
        
        const labelEl = document.createElement('label');
        labelEl.className = 'a2ui-form-label';
        labelEl.textContent = label;
        container.appendChild(labelEl);
        
        const input = document.createElement('input');
        input.type = 'file';
        input.className = 'a2ui-form-input';
        input.accept = accept;
        input.multiple = multiple;
        
        const statusEl = document.createElement('div');
        statusEl.className = 'a2ui-text caption';
        statusEl.style.marginTop = '8px';
        
        input.addEventListener('change', async (e) => {
            const files = Array.from(e.target.files);
            if (files.length === 0) return;
            
            for (const file of files) {
                if (file.size > maxSize) {
                    statusEl.textContent = `❌ File too large: ${file.name}`;
                    continue;
                }
                
                statusEl.textContent = `⏳ Uploading ${file.name}...`;
                
                try {
                    const uploaded = await this.uploadFile(file);
                    statusEl.textContent = `✅ Uploaded: ${file.name}`;
                    this.handleAction('fileUploaded', id, { file: uploaded });
                } catch (err) {
                    statusEl.textContent = `❌ Failed: ${file.name}`;
                    console.error('Upload error:', err);
                }
            }
        });
        
        container.appendChild(input);
        container.appendChild(statusEl);
        
        return container;
    }

    /**
     * Upload file to backend
     */
    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('sessionId', this.sessionId);
        
        const response = await fetch(`${this.apiBaseUrl}/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Upload failed');
        }
        
        return await response.json();
    }

    /**
     * DatePicker component
     */
    createDatePickerComponent(id, properties) {
        const label = this.resolveValue(properties.label) || '';
        const placeholder = this.resolveValue(properties.placeholder) || '';
        const valuePath = properties.value?.path;
        const value = valuePath ? this.getPathValue(valuePath) : '';
        const mode = properties.mode || 'date'; // 'date', 'time', 'datetime'
        const minDate = properties.minDate || '';
        const maxDate = properties.maxDate || '';
        
        const container = document.createElement('div');
        container.className = 'a2ui-datepicker';
        container.dataset.componentId = id;
        
        if (label) {
            const labelEl = document.createElement('label');
            labelEl.className = 'a2ui-datepicker-label';
            labelEl.textContent = label;
            container.appendChild(labelEl);
        }
        
        const input = document.createElement('input');
        input.className = 'a2ui-datepicker-input';
        
        if (mode === 'date') {
            input.type = 'date';
        } else if (mode === 'time') {
            input.type = 'time';
        } else {
            input.type = 'datetime-local';
        }
        
        input.placeholder = placeholder;
        input.value = value || '';
        
        if (minDate) input.min = minDate;
        if (maxDate) input.max = maxDate;
        
        input.addEventListener('change', (e) => {
            if (valuePath) {
                this.setPathValue(valuePath, e.target.value);
            }
            this.handleAction('change', id, { value: e.target.value });
        });
        
        container.appendChild(input);
        return container;
    }

    /**
     * TextArea component
     */
    createTextAreaComponent(id, properties) {
        const label = this.resolveValue(properties.label) || '';
        const placeholder = this.resolveValue(properties.placeholder) || '';
        const valuePath = properties.value?.path;
        const value = valuePath ? this.getPathValue(valuePath) : '';
        const rows = properties.rows || 4;
        const maxLength = properties.maxLength || null;
        const showCounter = properties.showCounter || false;
        
        const container = document.createElement('div');
        container.className = 'a2ui-textarea';
        container.dataset.componentId = id;
        
        if (label) {
            const labelEl = document.createElement('label');
            labelEl.className = 'a2ui-textarea-label';
            labelEl.textContent = label;
            container.appendChild(labelEl);
        }
        
        const textarea = document.createElement('textarea');
        textarea.className = 'a2ui-textarea-input';
        textarea.placeholder = placeholder;
        textarea.value = value || '';
        textarea.rows = rows;
        
        if (maxLength) {
            textarea.maxLength = maxLength;
        }
        
        textarea.addEventListener('input', (e) => {
            if (valuePath) {
                this.setPathValue(valuePath, e.target.value);
            }
            // Update counter if shown
            if (showCounter && counterEl) {
                counterEl.textContent = `${e.target.value.length}${maxLength ? ' / ' + maxLength : ''}`;
            }
        });
        
        container.appendChild(textarea);
        
        // Add counter if requested
        if (showCounter) {
            const counterEl = document.createElement('div');
            counterEl.className = 'a2ui-textarea-counter';
            counterEl.textContent = `${(value || '').length}${maxLength ? ' / ' + maxLength : ''}`;
            container.appendChild(counterEl);
        }
        
        return container;
    }

    // ==================== Helpers ====================

    /**
     * Get child components
     */
    getChildren(properties) {
        const children = properties.children;
        if (!children) return [];
        
        if (children.explicitList) {
            return children.explicitList
                .map(id => this.components.get(id))
                .filter(Boolean);
        }
        
        return [];
    }

    /**
     * Resolve list items from data binding or explicit list
     */
    resolveListItems(properties) {
        const children = properties.children;
        if (!children) return [];
        
        // Try data binding first
        if (children.template && children.template.dataBinding) {
            const items = this.getPathValue(children.template.dataBinding);
            if (Array.isArray(items)) {
                return items;
            }
        }
        
        // Fallback to explicit list
        if (children.explicitList) {
            return children.explicitList.map(id => {
                const comp = this.components.get(id);
                return comp ? this.resolveValue(comp.properties.text) : id;
            });
        }
        
        return [];
    }

    /**
     * Handle component actions
     */
    handleAction(action, componentId, data = {}) {
        const payload = {
            type: 'action',
            action,
            componentId,
            data,
            sessionId: this.sessionId,
            timestamp: Date.now()
        };
        
        this.sendData(payload);
    }

    /**
     * Render direct component (non-standard)
     */
    renderDirect(message) {
        if (Array.isArray(message)) {
            message.forEach(comp => {
                const el = this.createComponentElement(comp);
                if (el) this.container.appendChild(el);
            });
        } else if (message.type) {
            const el = this.createComponentElement(message);
            if (el) this.container.appendChild(el);
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        this.container.innerHTML = `<div class="a2ui-error">${message}</div>`;
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { A2UIRenderer };
}

(function ($) {
    app.modals.CreateOrEditProjectInfoModal = function () {
        const _mainService = abp.services.app.projectInfo;
        const OCR_API_URL = 'https://unrevocably-cheerless-youlanda.ngrok-free.dev';
        const OCR_WS_URL = 'wss://unrevocably-cheerless-youlanda.ngrok-free.dev'; // wss cho ngrok https

        let _modalManager;
        let _mainForm = null;
        let _detailForm = null;
        let _detailTable = null;
        let _modal;
        let attachFile;
        let attachFileName;
        let attachFileToken;
        let attachFileTokenCountDown;
        let btnUpload;
        let ocrWebSocket = null; // WebSocket connection

        this.init = function (modalManager) {
            _modalManager = modalManager;
            _modal = _modalManager.getModal();
            _modalManager.bigModal();
            _modalManager.initControl();

            _mainForm = _modal.find('form[name=MainForm]');
            _detailForm = _modal.find('form[id=DetailForm]');
            _mainForm.validate();
            _detailForm.validate();
            _detailTable = _modal.find('#DetailTable');
            btnUpload = _modal.find(".btnUpload");
            attachFile = _modal.find('#attachFile');
            attachFileName = _modal.find('#attachFileName');
            attachFileToken = _modal.find('#attachFileToken');
            attachFileTokenCountDown = _modal.find('#attachFileTokenExpiredCountDown');

            btnUpload.click(function () {
                _modal.find("#attachFile").trigger("click")
            });

            attachFile.on('change', function (e) {
                const fileName = e.target.files[0].name;
                attachFileName.val(fileName);
                let fileToken = app.guid();
                let fd = new FormData();
                fd.append('file', e.target.files[0]);
                fd.append('fileName', e.target.files[0].name);
                fd.append('fileToken', fileToken);
                _modalManager.setBusy(true);
                $.ajax({
                    url: '/App/FilesManager/UploadTempFile',
                    data: fd,
                    processData: false,
                    contentType: false,
                    type: 'POST',
                    success: function (data) {
                        attachFileTokenCountDown.removeClass('hidden');
                        attachFileTokenCountDown.countdown(moment().add(30, 'minutes').toDate(), function (event) {
                            $(this).val(event.strftime('%M:%S'));
                        });
                        attachFileToken.val(fileToken);
                        _modalManager.setBusy(false);
                    },
                    error: function () {
                        alert(app.localize('UploadError'));
                        _modalManager.setBusy(false);
                    }
                });
            });

            // ========== AI OCR với WebSocket ==========
            let btnAiOcr = _modal.find('#btnAiOcr');
            btnAiOcr.click(function (e) {
                e.preventDefault();
                let fileToken = attachFileToken.val();
                if (!fileToken) {
                    abp.message.warn('Vui lòng upload file trước');
                    return;
                }
                
                _modalManager.setBusy(true);
                
                // Lấy đường dẫn file
                $.post('/Dms/ProjectInfo/GetFileFullPath', { fileToken: fileToken }, function (response) {
                    if (!response.result || !response.result.success || !response.result.fullPath) {
                        abp.message.error('Không lấy được đường dẫn file');
                        _modalManager.setBusy(false);
                        return;
                    }
                    
                    let fullUrl = 'https://qlda.lamhai.net' + response.result.fullPath;
                    console.log('📄 File URL:', fullUrl);
                    
                    // Gọi hàm xử lý OCR với WebSocket
                    processOCRWithWebSocket(fullUrl);
                });
            });

            // Hàm xử lý OCR với WebSocket
            function processOCRWithWebSocket(fileUrl) {
                // Step 1: Upload file to OCR server
                $.ajax({
                    url: OCR_API_URL + '/api/v1/documents/upload_from_url',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ url: fileUrl, dpi: '300' }),
                    success: function(uploadResult) {
                        console.log('✅ Upload thành công:', uploadResult);
                        
                        if (uploadResult.status === 'success' && uploadResult.document_id) {
                            let documentId = uploadResult.document_id;
                            
                            // Step 2: Kết nối WebSocket TRƯỚC KHI bắt đầu OCR
                            connectWebSocket(documentId);
                            
                            // Step 3: Bắt đầu OCR
                            $.ajax({
                                url: OCR_API_URL + '/api/v1/documents/' + documentId + '/extract_full_async?dpi=300',
                                method: 'POST',
                                success: function(ocrStart) {
                                    console.log('🚀 OCR bắt đầu:', ocrStart.message);
                                    abp.message.info('Đang xử lý OCR, vui lòng đợi...');
                                },
                                error: function(err) {
                                    console.error('❌ Lỗi bắt đầu OCR:', err);
                                    abp.message.error('Lỗi bắt đầu OCR');
                                    _modalManager.setBusy(false);
                                    closeWebSocket();
                                }
                            });
                        } else {
                            abp.message.error('Upload thất bại');
                            _modalManager.setBusy(false);
                        }
                    },
                    error: function(err) {
                        console.error('❌ Upload error:', err);
                        abp.message.error('Lỗi upload: ' + (err.responseJSON?.message || err.statusText));
                        _modalManager.setBusy(false);
                    }
                });
            }

            // Kết nối WebSocket
            function connectWebSocket(documentId) {
                console.log('🔌 Đang kết nối WebSocket cho document:', documentId);
                
                ocrWebSocket = new WebSocket(OCR_WS_URL + '/ws/' + documentId);
                
                ocrWebSocket.onopen = function() {
                    console.log('✅ WebSocket connected');
                };
                
                ocrWebSocket.onmessage = function(event) {
                    let data = JSON.parse(event.data);
                    console.log('📨 WebSocket message:', data);
                    
                    // Nhận thông báo OCR hoàn thành
                    if (data.status === 'completed' || data.status === 'success') {
                        console.log('🎉 OCR hoàn thành!');
                        
                        // Tự động lấy kết quả
                        fetchExtractionResults(data.document_id);
                        
                        // Đóng WebSocket
                        closeWebSocket();
                    }
                };
                
                ocrWebSocket.onerror = function(error) {
                    console.error('❌ WebSocket error:', error);
                    abp.message.error('Lỗi kết nối WebSocket');
                    _modalManager.setBusy(false);
                };
                
                ocrWebSocket.onclose = function() {
                    console.log('🔌 WebSocket disconnected');
                };
                
                // Heartbeat để giữ kết nối
                let heartbeatInterval = setInterval(function() {
                    if (ocrWebSocket && ocrWebSocket.readyState === WebSocket.OPEN) {
                        ocrWebSocket.send('ping');
                    } else {
                        clearInterval(heartbeatInterval);
                    }
                }, 30000);
            }

            // Lấy kết quả extraction
            function fetchExtractionResults(documentId) {
                $.ajax({
                    url: OCR_API_URL + '/api/v1/documents/' + documentId + '/extractions',
                    method: 'GET',
                    headers: { 'ngrok-skip-browser-warning': 'true' },
                    success: function(extractResult) {
                        console.log('📊 Extract result:', extractResult);
                        
                        if (extractResult.status === 'success' && extractResult.extractions && extractResult.extractions.length > 0) {
                            // Fill dữ liệu vào form
                            fillFormData(extractResult.extractions[0]);
                            
                            abp.message.success('✅ Trích xuất thành công ' + extractResult.total_documents + ' văn bản!');
                        } else {
                            abp.message.warn('Không có dữ liệu trích xuất');
                        }
                        
                        _modalManager.setBusy(false);
                    },
                    error: function(err) {
                        console.error('❌ Extract error:', err);
                        abp.message.error('Lỗi lấy kết quả: ' + (err.responseJSON?.message || err.statusText));
                        _modalManager.setBusy(false);
                    }
                });
            }

            // Fill dữ liệu vào form
            function fillFormData(data) {
                console.log('📝 Filling form with data:', data);
                
                if (data.ten_du_an) $('#ProjectInfo_Name').val(data.ten_du_an);
                if (data.muc_tieu_du_an) $('#ProjectInfo_ProjectObjective').val(data.muc_tieu_du_an);
                if (data.quy_mo_dau_tu) $('#ProjectInfo_InvestmentScale').val(data.quy_mo_dau_tu);
                if (data.so_quyet_dinh) $('#ProjectInfo_DecisionCode').val(data.so_quyet_dinh);
                if (data.ngay_quyet_dinh) $('#ProjectInfo_DecisionDate').val(data.ngay_quyet_dinh);
                
                // Thêm các trường khác nếu cần
                if (data.chu_dau_tu) $('#ProjectInfo_Owner').val(data.chu_dau_tu);
                if (data.loai_nguon_von) $('#ProjectInfo_FundSource').val(data.loai_nguon_von);
            }

            // Đóng WebSocket
            function closeWebSocket() {
                if (ocrWebSocket) {
                    ocrWebSocket.close();
                    ocrWebSocket = null;
                }
            }

            // Đóng WebSocket khi đóng modal
            _modal.on('hidden.bs.modal', function () {
                closeWebSocket();
            });

            // ========== Detail Table ==========
            _detailTable.on('click', '#btnAddDetail', function () {
                abp.ui.setBusy(_detailTable);
                $.get(abp.appPath + 'Dms/ProjectInfo/NewDetail').always(function () {
                    abp.ui.clearBusy(_detailTable);
                }).then(function (res) {
                    _detailTable.find('.lastDetailRow').before(res);
                    baseHelper.RefreshUI(_detailTable);
                    InitDetailSelector();
                });
            })

            _detailTable.on('click', '.btnDeleteDetail', function () {
                let rowId = $(this).attr('rowId');
                _detailTable.find('.detailRow[rowId=' + rowId + ']').remove();
            });
            
            baseHelper.RefreshUI(_detailTable);
            InitDetailSelector();
        };

        function InitDetailSelector() {
            if (_detailTable) {
                _detailTable.find('.detailRow').each(function () {
                    let rowId = $(this).attr('rowId');
                    let citySelector = $(this).find('select.city');
                    if (!citySelector.data('select2')) {
                        baseHelper.Select2(citySelector, app.localize('SelectOne'), 'Dms/GetPagedCities', {
                            filterFunc: function () {
                                let selectedCityIds = [];
                                _detailTable.find('.detailRow[rowId!="' + rowId + '"]').each(function () {
                                    let prdId = $(this).find('select.city').val();
                                    if (prdId) {
                                        selectedCityIds.push(prdId);
                                    }
                                });

                                return {
                                    isActive: true,
                                    excludeIds: baseHelper.ParseArrayToList(selectedCityIds)
                                }
                            },
                            mapResultFunc: function (items) {
                                return $.map(items, function (item) {
                                    return {
                                        id: item.id,
                                        text: baseHelper.Select2Text([
                                            item.code,
                                            item.name
                                        ])
                                    }
                                });
                            },
                            onSelectFunc: function (item) {

                            },
                            onClearFunc: function () {

                            }
                        });
                    }

                    let wardSelector = $(this).find('select.ward');
                    if (!wardSelector.data('select2')) {
                        baseHelper.Select2(wardSelector, app.localize('SelectOne'), 'Dms/GetPagedWards', {
                            filterFunc: function () {
                                let selectedWardIds = [];
                                _detailTable.find('.detailRow[rowId!="' + rowId + '"]').each(function () {
                                    let prdId = $(this).find('select.city').val();
                                    if (prdId) {
                                        selectedWardIds.push(prdId);
                                    }
                                });

                                return {
                                    isActive: true,
                                    cityId: citySelector.val(),
                                    excludeIds: baseHelper.ParseArrayToList(selectedWardIds)
                                }
                            },
                            mapResultFunc: function (items) {
                                return $.map(items, function (item) {
                                    return {
                                        id: item.id,
                                        text: baseHelper.Select2Text([
                                            item.code,
                                            item.name
                                        ])
                                    }
                                });
                            }
                        });
                    }
                });
            }
        }

        function GetDetail() {
            let res = [];
            _detailTable.find('.detailRow').each(function () {
                let rowId = $(this).attr('rowId');
                let detail = {
                    projectInfoId: $(this).find('.projectInfoId').val(),
                    cityId: $(this).find('select.city').val(),
                    wardId: $(this).find('select.ward').val(),
                    location: $(this).find('.location').val(),
                };
                if ($(this).find('.detailId').exists()) {
                    detail.id = parseInt($(this).find('.detailId').val());
                }
                res.push(detail);
            });
            return res;
        }

        let projectOwnerSelector = $('#ProjectOwnerSelector');
        if (projectOwnerSelector.exists()) {
            baseHelper.Select2(projectOwnerSelector, app.localize('PleaseSelect'), 'Dms/GetPagedProjectOwners');
        }

        let projectStatusSelector = $('#ProjectStatusSelector');
        if (projectStatusSelector.exists()) {
            baseHelper.Select2(projectStatusSelector, app.localize('PleaseSelect'), 'Dms/GetPagedProjectStatuses');
        }
        let sectorCategorySelector = $('#SectorCategorySelector');
        if (sectorCategorySelector.exists()) {
            baseHelper.Select2(sectorCategorySelector, app.localize('PleaseSelect'), 'Dms/GetPagedSectorCategories');
        }
        let settlementAgencySelector = $('#SettlementAgencySelector');
        if (settlementAgencySelector.exists()) {
            baseHelper.Select2(settlementAgencySelector, app.localize('PleaseSelect'), 'Dms/GetPagedSettlementAgencies');
        }

        let projectTypeSelector = $('#ProjectTypeSelector');
        if (projectTypeSelector.exists()) {
            baseHelper.Select2(projectTypeSelector, app.localize('PleaseSelect'), 'Dms/GetPagedProjectTypes');
        }

        function CreateOrEdit() {
            let projectInfo = _mainForm.serializeFormToObject();
            projectInfo.projectInfoLocations = GetDetail();
            console.log(projectInfo);
            _modalManager.setBusy(true);
            _mainService.createOrEdit(
                projectInfo
            ).done(function () {
                abp.notify.info(app.localize('SavedSuccessfully'));
                _modalManager.close();
                abp.event.trigger('app.createOrEditProjectInfoModalSaved');
            }).always(function () {
                _modalManager.setBusy(false);
            });
        }

        this.save = function () {
            let detailValid = _detailForm.validate();
            let selectorValid = baseHelper.ValidSelectors(_detailForm);

            if (!_mainForm.valid() || !detailValid || !selectorValid) {
                return;
            }
            CreateOrEdit();
        };
    };
})(jQuery);

(function ($) {
   app.modals.CreateOrEditProjectInfoModal = function () {
       const _mainService = abp.services.app.projectInfo;

       let _modalManager;
       let _mainForm = null;
       let _detailForm = null;
       let _detailTable = null;
       let _modal;
       //
       let attachFile;
       let attachFileName;
       let attachFileToken;
       let attachFileTokenCountDown;
       let btnUpload;

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
           //
           btnUpload = _modal.find(".btnUpload");
           attachFile = _modal.find('#attachFile');
           attachFileName = _modal.find('#attachFileName');
           attachFileToken = _modal.find('#attachFileToken');
           attachFileTokenCountDown = _modal.find('#attachFileTokenExpiredCountDown');

           btnUpload.click(function () {
               _modal.find("#attachFile").trigger("click")
           });

           let currentFile = null;

           attachFile.on('change', function (e) {
               const file = e.target.files[0];
               if (!file) return;

               currentFile = file;
               const fileName = file.name;
               attachFileName.val(fileName);

               let fileToken = app.guid();
               let fd = new FormData();
               fd.append('file', file);
               fd.append('fileName', fileName);
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

           let btnAiOcr = _modal.find('#btnAiOcr');
           btnAiOcr.click(function (e) {
               e.preventDefault();

               if (!currentFile) {
                   abp.message.warn('Vui lòng upload file trước');
                   return;
               }

               _modalManager.setBusy(true);

               let fd = new FormData();
               fd.append('file', currentFile);
               fd.append('dpi', '300');

               console.log('Uploading file to AI server:', currentFile.name);

               // Upload file directly to AI server
               $.ajax({
                   url: 'https://unrevocably-cheerless-youlanda.ngrok-free.dev/api/v1/documents/upload',
                   method: 'POST',
                   data: fd,
                   processData: false,
                   contentType: false,
                   success: function(uploadResult) {
                       console.log('Upload result:', uploadResult);
                       abp.message.info('Upload thành công: ' + uploadResult.message);

                       if (uploadResult.status === 'success' && uploadResult.document_id) {
                           // Step 2: Get extractions
                           $.ajax({
                               url: 'https://unrevocably-cheerless-youlanda.ngrok-free.dev/api/v1/documents/' + uploadResult.document_id + '/extractions',
                               method: 'GET',
                               headers: { 'ngrok-skip-browser-warning': 'true' },
                               success: function(extractResult) {
                                   console.log('Extract result:', extractResult);
                                   console.log('Total documents:', extractResult.total_documents);
                                   console.log('Extractions:', JSON.stringify(extractResult.extractions, null, 2));

                                   if (extractResult.extractions && extractResult.extractions.length > 0) {
                                       var data = extractResult.extractions[0];
                                       if (data.ten_du_an) $('#ProjectInfo_Name').val(data.ten_du_an);
                                       if (data.muc_tieu_du_an) $('#ProjectInfo_ProjectObjective').val(data.muc_tieu_du_an);
                                       if (data.quy_mo_dau_tu) $('#ProjectInfo_InvestmentScale').val(data.quy_mo_dau_tu);
                                       if (data.so_quyet_dinh) $('#ProjectInfo_DecisionCode').val(data.so_quyet_dinh);
                                       if (data.ngay_quyet_dinh) $('#ProjectInfo_DecisionDate').val(data.ngay_quyet_dinh);
                                   }

                                   abp.message.success('Trích xuất thành công ' + extractResult.total_documents + ' văn bản!');
                                   _modalManager.setBusy(false);
                               },
                               error: function(err) {
                                   console.error('Extract error:', err);
                                   abp.message.error('Lỗi trích xuất: ' + (err.responseJSON?.message || err.statusText));
                                   _modalManager.setBusy(false);
                               }
                           });
                       } else {
                           _modalManager.setBusy(false);
                       }
                   },
                   error: function(err) {
                       console.error('Upload error:', err);
                       abp.message.error('Lỗi upload: ' + (err.responseJSON?.message || err.statusText));
                       _modalManager.setBusy(false);
                   }
               });
           });

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
           //
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
               //
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
           //
           CreateOrEdit();
       };
   };
})(jQuery);


// (function ($) {
//     app.modals.CreateOrEditProjectInfoModal = function () {
//         const _mainService = abp.services.app.projectInfo;
//         const OCR_API_URL = 'https://unrevocably-cheerless-youlanda.ngrok-free.dev';
//         const OCR_WS_URL = 'wss://unrevocably-cheerless-youlanda.ngrok-free.dev'; // wss cho ngrok https

//         let _modal;
//         let _modalManager;
//         let _mainForm = null;
//         let _detailForm = null;
//         let _detailTable = null;
//         let _locationTable = null;
//         let _locationForm = null;
//         //
//         let attachFile;
//         let attachFileName;
//         let attachFileToken;
//         let attachFileTokenCountDown;
//         let btnUpload;
//         let ocrWebSocket = null;

//         this.init = function (modalManager) {
//             _modalManager = modalManager;
//             _modal = _modalManager.getModal();
//             _modalManager.bigModal();
//             _modalManager.initControl();

//             _mainForm = _modal.find('form[name=MainForm]');
//             _detailForm = _modal.find('form[id=DetailForm]');
//             _locationForm = _modal.find('form[id=LocationForm]');
//             _mainForm.validate();
//             _detailForm.validate();
//             _locationForm.validate();
//             _detailTable = _modal.find('#DetailTable');
//             _locationTable = _modal.find('#LocationTable');

//             btnUpload = _modal.find(".btnUpload");
//             attachFile = _modal.find('#attachFile');
//             attachFileName = _modal.find('#attachFileName');
//             attachFileToken = _modal.find('#attachFileToken');
//             attachFileTokenCountDown = _modal.find('#attachFileTokenExpiredCountDown');

//             _locationTable.on('click', '#btnAddDetail', function () {
//                 abp.ui.setBusy(_locationTable);
//                 $.get(abp.appPath + 'Dms/ProjectInfo/NewLocation').always(function () {
//                     abp.ui.clearBusy(_locationTable);
//                 }).then(function (res) {
//                     _locationTable.find('.lastDetailRow').before(res);
//                     baseHelper.RefreshUI(_locationTable);
//                     InitLocationSelector();
//                     PopulateTotal();
//                 });
//             })

//             _locationTable.on('click', '.btnDeleteDetail', function () {
//                 let rowId = $(this).attr('rowId');
//                 _locationTable.find('.detailRow[rowId=' + rowId + ']').remove();
//                 PopulateTotal();
//             });

//             let btnAiOcr = _modal.find('#btnAiOcr');
//             console.log('btnAiOcr found:', btnAiOcr.length);
//             btnAiOcr.click(function (e) {
//                 e.preventDefault();
//                 console.log('AI OCR clicked');
//                 let fileToken = attachFileToken.val();
//                 console.log('fileToken:', fileToken);
//                 if (!fileToken) {
//                     abp.message.warn('Vui lòng upload file trước');
//                     return;
//                 }
//                 console.log('Calling API...');
//                 $.post('/Dms/ProjectInfo/GetFileFullPath', { fileToken: fileToken }, function (response) {
//                     console.log('API result:', response);
//                     if (response.result && response.result.success && response.result.fullPath) {
//                         let fullUrl = window.location.origin + response.result.fullPath;
//                         abp.message.info('File URL: ' + fullUrl);
//                     }
//                 });
//             });

//             _detailTable.on('click', '#btnAddDetail', function () {
//                 abp.ui.setBusy(_detailTable);
//                 $.get(abp.appPath + 'Dms/ProjectInfo/NewDetail').always(function () {
//                     abp.ui.clearBusy(_detailTable);
//                 }).then(function (res) {
//                     _detailTable.find('.lastDetailRow').before(res);
//                     baseHelper.RefreshUI(_detailTable);
//                     InitDetailSelector();
//                 });
//             })

//             _detailTable.on('click', '.btnDeleteDetail', function () {
//                 let rowId = $(this).attr('rowId');
//                 _detailTable.find('.detailRow[rowId=' + rowId + ']').remove();
//             });
//             //
//             baseHelper.RefreshUI(_detailTable);
//             InitDetailSelector();
//         };

//         function InitLocationSelector() {
//             if (_locationTable) {
//                 _locationTable.find('.detailRow').each(function () {
//                     let rowId = $(this).attr('rowId');

//                     let citySelector = $(this).find('select.city');
//                     if (!citySelector.data('select2')) {
//                         baseHelper.Select2(citySelector, app.localize('PleaseSelect'), 'Dms/GetPagedCities', {
//                             filterFunc: function () {
//                                 let selectedCityIds = [];
//                                 _locationTable.find('.detailRow[rowId!="' + rowId + '"]').each(function () {
//                                     let cityId = $(this).find('select.city').val();
//                                     if (cityId) {
//                                         selectedCityIds.push(cityId);
//                                     }
//                                 });

//                                 return {
//                                     excludeIds: baseHelper.ParseArrayToList(selectedCityIds)
//                                 }
//                             },
//                             mapResultFunc: function (items) {
//                                 return $.map(items, function (item) {
//                                     return {
//                                         id: item.id,
//                                         text: baseHelper.Select2Text([item.code, item.name])
//                                     }
//                                 });
//                             },
//                             onSelectFunc: function (item) {
//                                 wardSelector.val('0').trigger('change');
//                             },
//                             onClearFunc: function () {
//                                 wardSelector.val('0').trigger('change');
//                             }
//                         });
//                     }

//                     let wardSelector = $(this).find('select.ward');
//                     if (!wardSelector.data('select2')) {
//                         baseHelper.Select2(wardSelector, app.localize('PleaseSelect'), 'Dms/GetPagedWards', {
//                             filterFunc: function () {
//                                 let selectedWardIds = [];
//                                 _locationTable.find('.detailRow[rowId!="' + rowId + '"]').each(function () {
//                                     let wardId = $(this).find('select.ward').val();
//                                     if (wardId) {
//                                         selectedWardIds.push(wardId);
//                                     }
//                                 });

//                                 return {
//                                     cityId: citySelector.val(),
//                                     excludeIds: baseHelper.ParseArrayToList(selectedWardIds)
//                                 }
//                             },
//                             mapResultFunc: function (items) {
//                                 return $.map(items, function (item) {
//                                     return {
//                                         id: item.id,
//                                         text: baseHelper.Select2Text([item.code, item.name])
//                                     }
//                                 });
//                             },
//                             onSelectFunc: function (item) {
//                             },
//                             onClearFunc: function () {
//                             }
//                         });
//                     }
//                     //
//                 });
//             }
//         }

//         function PopulateTotal() {
//             //		
//         }

//         function GetLocation() {
//             let res = [];
//             _locationTable.find('.detailRow').each(function () {
//                 let rowId = $(this).attr('rowId');
//                 let detail = {

//                     projectInfoId: $(this).find('.projectInfoId[rowId="' + rowId + '"]').val(),
//                     cityId: $(this).find('#city_' + rowId).val(),
//                     wardId: $(this).find('#ward_' + rowId).val(),
//                     location: $(this).find('.location').val()
//                 };
//                 if ($(this).find('.detailId').exists()) {
//                     detail.id = parseInt($(this).find('.detailId').val());
//                 }
//                 res.push(detail);
//             });
//             return res;
//         }

//         let projectOwnerSelector = $('#ProjectOwnerSelector');
//         if (projectOwnerSelector.exists()) {
//             baseHelper.Select2(projectOwnerSelector, app.localize('PleaseSelect'), 'Dms/GetPagedProjectOwners');
//             //
//             projectOwnerSelector.on('change', function () {
//                 investmentPolicySelector.val('0').trigger('change');
//             })
//         }

//         let investmentPolicySelector = $('#InvestmentPolicySelector');
//         if (investmentPolicySelector.exists()) {
//             baseHelper.Select2(investmentPolicySelector, app.localize('PleaseSelect'), 'Dms/GetPagedInvestmentPolicies', {
//                 filterFunc: function () {

//                     return {
//                         projectOwnerId: projectOwnerSelector.val()
//                     }
//                 },
//                 mapResultFunc: function (items) {
//                     return $.map(items, function (item) {
//                         return {
//                             id: item.id,
//                             text: baseHelper.Select2Text([item.decisionCode, baseHelper.ShowDate(item.decisionDate)])
//                         }
//                     });
//                 }
//             });
//             //
//             investmentPolicySelector.on('change', function () {
//                 //
//             })
//         }
//         let projectStatusSelector = $('#ProjectStatusSelector');
//         if (projectStatusSelector.exists()) {
//             baseHelper.Select2(projectStatusSelector, app.localize('PleaseSelect'), 'Dms/GetPagedProjectStatuses');
//             //
//             projectStatusSelector.on('change', function () {
//                 //
//             })
//         }
//         let sectorCategorySelector = $('#SectorCategorySelector');
//         if (sectorCategorySelector.exists()) {
//             baseHelper.Select2(sectorCategorySelector, app.localize('PleaseSelect'), 'Dms/GetPagedSectorCategories');
//             //
//             sectorCategorySelector.on('change', function () {
//                 //
//             })
//         }
//         let settlementAgencySelector = $('#SettlementAgencySelector');
//         if (settlementAgencySelector.exists()) {
//             baseHelper.Select2(settlementAgencySelector, app.localize('PleaseSelect'), 'Dms/GetPagedSettlementAgencies');
//             //
//             settlementAgencySelector.on('change', function () {
//                 //
//             })
//         }
//         let projectTypeSelector = $('#ProjectTypeSelector');
//         if (projectTypeSelector.exists()) {
//             baseHelper.Select2(projectTypeSelector, app.localize('PleaseSelect'), 'Dms/GetPagedProjectTypes');
//             //
//             projectTypeSelector.on('change', function () {
//                 //
//             })
//         }
//         let btnUpload2 = $('.btnUpload');
//         if (btnUpload2.exists()) {
//             btnUpload2.click(function () {
//                 $('#attachFile').trigger("click")
//             })
//         }
//         //
//         let attachFile2 = $('#attachFile');
//         if (attachFile2.exists()) {
//             let attachFileName2 = $('#attachFileName');
//             let attachFileToken2 = $('#attachFileToken');
//             let attachFileTokenCountDown2 = $('#attachFileTokenExpiredCountDown'); // modal.find
//             //
//             attachFile2.on('change', function (e) {
//                 const fileName = e.target.files[0].name;
//                 attachFileName2.val(fileName);
//                 let fd = new FormData();
//                 fd.append('file', e.target.files[0]);
//                 fd.append('fileName', e.target.files[0].name);
//                 fd.append('fileToken', app.guid());
//                 _modalManager.setBusy(true);
//                 $.ajax({
//                     url: '/App/FilesManager/UploadTempFile',
//                     data: fd,
//                     processData: false,
//                     contentType: false,
//                     type: 'POST',
//                     success: function (data) {
//                         attachFileTokenCountDown2.removeClass('hidden');
//                         attachFileTokenCountDown2.countdown(moment().add(30, 'minutes').toDate(), function (event) {
//                             $(this).val(event.strftime('%M:%S'));
//                         });
//                         attachFileToken2.val(data.fileToken);
//                         _modalManager.setBusy(false);
//                     },
//                     error: function () {
//                         alert(app.localize('UploadError'));
//                         _modalManager.setBusy(false);
//                     }
//                 });
//             })
//         }

//         function CreateOrEdit() {
//             let projectInfo = _mainForm.serializeFormToObject();
//             projectInfo.lstLocation = GetLocation();

//             _modalManager.setBusy(true);
//             _mainService.createOrEdit(
//                 projectInfo
//             ).done(function () {
//                 abp.notify.info(app.localize('SavedSuccessfully'));
//                 _modalManager.close();
//                 abp.event.trigger('app.createOrEditProjectInfoModalSaved');
//             }).always(function () {
//                 _modalManager.setBusy(false);
//             });
//         }

//         this.save = function () {
//             let detailValid = _locationForm.validate();
//             let selectorValid = baseHelper.ValidSelectors(_locationForm);

//             if (!_mainForm.valid() || !detailValid || !selectorValid) {
//                 return;
//             }
//             CreateOrEdit();
//         };
//     };
// })(jQuery);
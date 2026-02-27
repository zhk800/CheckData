"""
标注自动修复程序

功能：
1. 删除无效的ScoreboardSingle标注（画面中无计分板）
2. 修复空间关系问题中的冗余描述（移除"on the left/right"等位置词）

特点：
- 仅传输关键信息（question/answer/labels），token消耗减少85%
- 支持超大批处理（100个文件/批）
- 一次API调用处理多个文件
"""

import os
import json
import time
from pathlib import Path
from google import genai


class AnnotationFixer:
    def __init__(self, api_key=None, batch_size=100):
        """
        初始化标注修复器
        
        Args:
            api_key: Gemini API密钥，如果为None则从环境变量GEMINI_API_KEY读取
            batch_size: 每批处理的文件数量（默认100）
        """
        if api_key:
            os.environ['GEMINI_API_KEY'] = api_key
        
        self.client = genai.Client()
        self.prompt_template = self._load_prompt()
        self.batch_size = batch_size
        self.stats = {
            'total_files': 0,
            'total_annotations': 0,
            'deleted_annotations': 0,
            'updated_annotations': 0,
            'errors': 0
        }
    
    def _load_prompt(self):
        """加载提示词模板"""
        prompt_path = Path(__file__).parent / 'prompt.md'
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _extract_key_info(self, json_data):
        """从完整JSON中提取关键信息"""
        key_info = {
            "scoreboard": [],
            "spatial": []
        }
        
        for ann in json_data.get('annotations', []):
            task_type = ann.get('task_L2', '')
            
            if task_type == 'ScoreboardSingle':
                key_info['scoreboard'].append({
                    'idx': ann.get('annotation_id'),
                    'question': ann.get('question', ''),
                    'answer': ann.get('answer', '')
                })
            
            elif task_type == 'Objects_Spatial_Relationships':
                # 提取labels
                labels = []
                bbox = ann.get('bounding_box', [])
                if isinstance(bbox, list):
                    for item in bbox:
                        if isinstance(item, dict) and 'label' in item:
                            labels.append(item['label'])
                
                key_info['spatial'].append({
                    'idx': ann.get('annotation_id'),
                    'question': ann.get('question', ''),
                    'answer': ann.get('answer', ''),
                    'labels': labels
                })
        
        return key_info
    
    def _apply_fixes(self, original_data, fixes):
        """应用修复指令到原始JSON数据"""
        fixed_data = json.loads(json.dumps(original_data))  # 深拷贝
        
        # 构建索引映射
        annotations_to_delete = set()
        annotations_to_update = {}
        
        # 处理scoreboard修复
        for fix in fixes.get('scoreboard', []):
            idx = fix.get('idx')
            action = fix.get('action')
            
            if action == 'delete':
                annotations_to_delete.add(idx)
                self.stats['deleted_annotations'] += 1
        
        # 处理spatial修复
        for fix in fixes.get('spatial', []):
            idx = fix.get('idx')
            action = fix.get('action')
            
            if action == 'delete':
                annotations_to_delete.add(idx)
                self.stats['deleted_annotations'] += 1
            elif action == 'update':
                annotations_to_update[idx] = {
                    'question': fix.get('question'),
                    'answer': fix.get('answer')
                }
                self.stats['updated_annotations'] += 1
        
        # 应用更新
        new_annotations = []
        for ann in fixed_data.get('annotations', []):
            idx = ann.get('annotation_id')
            
            if idx in annotations_to_delete:
                continue
            
            if idx in annotations_to_update:
                update = annotations_to_update[idx]
                if update['question']:
                    ann['question'] = update['question']
                if update['answer']:
                    ann['answer'] = update['answer']
            
            new_annotations.append(ann)
        
        fixed_data['annotations'] = new_annotations
        return fixed_data
    
    def fix_batch(self, json_files):
        """批量修复多个文件"""
        results = {}
        
        print(f"  📦 [1/4] 读取文件...")
        
        try:
            # 1. 读取所有文件并提取关键信息
            batch_data = {}
            file_data_map = {}
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        full_data = json.load(f)
                    
                    file_id = full_data.get('id', json_file.stem)
                    key_info = self._extract_key_info(full_data)
                    
                    if key_info['scoreboard'] or key_info['spatial']:
                        batch_data[file_id] = key_info
                        file_data_map[file_id] = {
                            'path': json_file,
                            'full_data': full_data
                        }
                    else:
                        results[str(json_file)] = (True, None, "No relevant annotations")
                
                except Exception as e:
                    results[str(json_file)] = (False, None, f"读取失败: {str(e)}")
                    self.stats['errors'] += 1
            
            if not batch_data:
                print(f"  ⚪ 无相关标注需要处理")
                return results
            
            print(f"  📦 [2/4] 打包数据... ({len(batch_data)}个文件，{len(json.dumps(batch_data, ensure_ascii=False))}字符)")
            
            # 2. 构建批量提示词
            batch_prompt = f"""{self.prompt_template}

## 待处理数据
```json
{json.dumps(batch_data, indent=2, ensure_ascii=False)}
```

请返回修复指令："""
            
            print(f"  🚀 [3/4] 调用API处理...")
            
            # 3. 调用API
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=batch_prompt,
            )
            
            print(f"  ✅ API响应成功")
            print(f"  📝 [4/4] 应用修复...")
            
            # 4. 解析响应
            response_text = response.text.strip()
            
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                if lines[0].strip() in ['```json', '```']:
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                response_text = '\n'.join(lines)
            
            fixes_batch = json.loads(response_text)
            
            # 5. 应用修复到每个文件
            for file_id, fixes in fixes_batch.items():
                if file_id not in file_data_map:
                    continue
                
                file_info = file_data_map[file_id]
                json_file = file_info['path']
                original_data = file_info['full_data']
                
                fixed_data = self._apply_fixes(original_data, fixes)
                
                # 写入文件
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(fixed_data, f, indent=2, ensure_ascii=False)
                
                self.stats['total_files'] += 1
                self.stats['total_annotations'] += len(original_data.get('annotations', []))
                
                # 检查修改
                orig_count = len(original_data.get('annotations', []))
                fixed_count = len(fixed_data.get('annotations', []))
                
                if orig_count != fixed_count:
                    results[str(json_file)] = (True, fixed_data, f"{orig_count} -> {fixed_count} annotations")
                else:
                    has_update = any(fix.get('action') == 'update' for fix in fixes.get('spatial', []))
                    if has_update:
                        results[str(json_file)] = (True, fixed_data, "Updated")
                    else:
                        results[str(json_file)] = (True, fixed_data, "No changes")
        
        except json.JSONDecodeError as e:
            error_msg = f"JSON解析错误: {str(e)}\n响应: {response_text[:300]}..."
            print(f"❌ 批量处理失败: {error_msg}")
            for file_id in batch_data.keys():
                file_path = str(file_data_map[file_id]['path'])
                if file_path not in results:
                    results[file_path] = (False, None, error_msg)
                    self.stats['errors'] += 1
        
        except Exception as e:
            error_msg = f"处理错误: {str(e)}"
            print(f"❌ 批量处理失败: {error_msg}")
            for file_id in batch_data.keys():
                file_path = str(file_data_map[file_id]['path'])
                if file_path not in results:
                    results[file_path] = (False, None, error_msg)
                    self.stats['errors'] += 1
        
        return results
    
    def fix_sport(self, sport_dir, delay=1.5):
        """处理单个运动项目"""
        sport_path = Path(sport_dir)
        json_files = sorted(list(sport_path.glob("**/frames/*.json")))
        
        if not json_files:
            print(f"❌ 未找到frames目录下的JSON文件")
            return
        
        sport_name = sport_path.name
        print(f"\n{'='*80}")
        print(f"🏅 {sport_name}")
        print(f"📁 找到 {len(json_files)} 个JSON文件")
        print(f"📦 批处理大小: {self.batch_size} 个文件/批次")
        print(f"{'='*80}\n")
        
        total_batches = (len(json_files) + self.batch_size - 1) // self.batch_size
        
        for batch_idx in range(0, len(json_files), self.batch_size):
            batch_files = json_files[batch_idx:batch_idx + self.batch_size]
            current_batch = batch_idx // self.batch_size + 1
            
            print(f"{'='*80}")
            print(f"📦 批次 {current_batch}/{total_batches} - 处理 {len(batch_files)} 个文件")
            print(f"{'='*80}")
            
            results = self.fix_batch(batch_files)
            
            # 显示结果
            for file_path_str, (success, fixed_data, msg) in results.items():
                file_name = Path(file_path_str).name
                if success:
                    if "No changes" in msg or "No relevant" in msg:
                        print(f"  ⚪ {file_name}: {msg}")
                    else:
                        print(f"  ✅ {file_name}: {msg}")
                else:
                    print(f"  ❌ {file_name}: {msg}")
            
            print(f"")
            
            if current_batch < total_batches:
                print(f"⏳ 等待 {delay} 秒后继续下一批...\n")
                time.sleep(delay)
        
        # 统计信息
        print(f"\n{'='*80}")
        print("📊 修复统计:")
        print(f"  总文件数: {self.stats['total_files']}")
        print(f"  总标注数: {self.stats['total_annotations']}")
        print(f"  删除标注: {self.stats['deleted_annotations']}")
        print(f"  更新标注: {self.stats['updated_annotations']}")
        print(f"  错误: {self.stats['errors']}")
        print(f"{'='*80}\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='标注自动修复程序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理单个运动项目
  python fix_frame.py Artistic_Swimming
  python fix_frame.py Badminton
  
  # 处理所有运动项目（默认）
  python fix_frame.py
        """
    )
    parser.add_argument('sport', nargs='?', help='运动项目名称（可选，不指定则处理所有）')
    parser.add_argument('--batch-size', '-b', type=int, default=100, help='批处理大小（默认100）')
    parser.add_argument('--delay', type=float, default=1.5, help='批次间延迟秒数（默认1.5）')
    parser.add_argument('--api-key', help='Gemini API密钥（可选，默认从环境变量读取）')
    
    args = parser.parse_args()
    
    # 检查API密钥
    if not args.api_key and not os.getenv('GEMINI_API_KEY'):
        print("❌ 请先设置GEMINI_API_KEY环境变量或使用--api-key参数")
        return
    
    # 确定输出目录
    output_base = Path(__file__).parent.parent / 'output'
    
    if args.sport:
        # 处理单个运动项目
        sport_dir = output_base / args.sport
        if not sport_dir.exists():
            print(f"❌ 运动项目不存在: {args.sport}")
            print(f"   路径: {sport_dir}")
            return
        
        fixer = AnnotationFixer(api_key=args.api_key, batch_size=args.batch_size)
        fixer.fix_sport(sport_dir, delay=args.delay)
    else:
        # 处理所有运动项目
        all_sports = sorted([d for d in output_base.iterdir() if d.is_dir()])
        
        if not all_sports:
            print(f"❌ 未找到运动项目目录")
            return
        
        print(f"\n🏆 准备处理 {len(all_sports)} 个运动项目")
        print(f"{'='*80}")
        for sport_dir in all_sports:
            print(f"  - {sport_dir.name}")
        print(f"{'='*80}\n")
        
        for i, sport_dir in enumerate(all_sports, 1):
            print(f"\n>>> 进度: {i}/{len(all_sports)}")
            fixer = AnnotationFixer(api_key=args.api_key, batch_size=args.batch_size)
            fixer.fix_sport(sport_dir, delay=args.delay)
        
        print(f"\n🎉 所有运动项目处理完成！")


if __name__ == '__main__':
    main()

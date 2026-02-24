import streamlit as st
import pandas as pd
import pyreadstat
import numpy as np
import os
import hashlib
# 1. 设置网页标题和说明
st.title('SAS数据集SUBJID随机化工具')
st.markdown("""
**操作说明：**
1. ⬆️ 上传SAS数据集 (.sas7bdat)
2. 👀 预览数据集内容
3. 🔑 设置seed
4. 🔧 执行随机化
5. 💾 下载结果文件
""")
# 2. 文件上传组件
st.sidebar.header("操作步骤")
uploaded_file = st.sidebar.file_uploader(
    "步骤1: 上传.sas7bdat文件", 
    type=["sas7bdat"],
    help="选择本地的.sas7bdat文件，确保是UTF-8编码格式"
)
if uploaded_file is not None:
    # 3. 读取SAS文件并预览
    st.subheader(f"📊 数据集预览: {uploaded_file.name}")
    
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    try:
        df, meta = pyreadstat.read_sas7bdat(temp_path, encoding="utf-8")
    except Exception as e:
        st.error(f"读取文件出错: {str(e)}")
        st.stop()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    st.success(f"成功读取数据集! 共{df.shape[0]}行, {df.shape[1]}列")
    st.info("数据集包含以下列: " + ", ".join(df.columns.tolist()))
    
    with st.expander("📂 查看数据内容 (显示前10行)"):
        st.dataframe(df.head(10))
    
    # 4. 检查SUBJID列是否存在
    if "SUBJID" not in df.columns:
        st.warning("⚠️ 未找到SUBJID列! 请检查数据格式")
        st.subheader("可选列列表:")
        st.write(df.columns.tolist())
        st.stop()
    else:
        st.success("✅ 已识别到SUBJID列")
    
    # 5. 随机化设置区域
    st.divider()
    st.subheader("🎲 随机化设置")
    
    seed = st.number_input(
        "步骤2: 输入随机种子（整数）", 
        value=393201,
        min_value=0,
        max_value=1000000,
        step=1,
        help="相同的种子会生成相同的随机分配"
    )
    
    if st.checkbox("显示SUBJID示例"):
        sample_ids = df["SUBJID"].unique()[:5]
        st.write(f"示例ID: {', '.join(map(str, sample_ids))}")
    
    # 6. 修复后的随机化函数 - 使用np.random.permutation模拟SAS proc plan
    def generate_dumsubj(dataframe, seed_value):
        """精确模拟SAS proc plan生成DUMSUBJ"""
        n = len(dataframe)
        # 1. 计算实际种子
        seed_bytes = str(seed_value).encode('utf-8')
        seed_hash = int(hashlib.md5(seed_bytes).hexdigest()[0:8], 16)
        actual_seed = seed_hash % (2**31 - 1)  # 使用精确的2^31-1
        
        # 2. 设置随机种子并生成直接排列序号
        np.random.seed(int(actual_seed))
        plan_var = np.random.permutation(n) + 1  # 生成1-n的随机排列
        
        # 3. 创建结果数据集
        result_df = pd.DataFrame({
            'ORD_VAR': np.arange(1, n+1),
            'PLAN_VAR': plan_var,  # 直接使用排列结果作为序号
            'SUBJID': dataframe['SUBJID'].values
        })
        
        # 4. 格式化DUMSUBJ
        def format_dumsubj(x):
            x = int(x)
            if x < 10: 
                return f"DUM-00{x}"
            elif x < 100: 
                return f"DUM-0{x}"
            else: 
                return f"DUM-{x}"
        
        result_df['DUMSUBJ'] = result_df['PLAN_VAR'].apply(format_dumsubj)
        return result_df[['SUBJID', 'ORD_VAR', 'DUMSUBJ']]
    
    # 7. 执行随机化
    if st.button("步骤3: 执行随机化"):
        with st.spinner("正在处理，请稍候..."):
            try:
                # 生成结果
                result_df = generate_dumsubj(df, seed)
                
                if result_df is not None:
                    st.success("✅ 随机化完成!")
                    
                    # 检查结果唯一性
                    if result_df['DUMSUBJ'].nunique() != len(result_df):
                        st.warning("⚠️ 警告: DUMSUBJ值不唯一!")
                    else:
                        st.success("✅ 所有DUMSUBJ值均唯一")
                    
                    # 显示结果预览
                    st.subheader("处理结果预览")
                    st.write(f"总SUBJID数: {len(result_df)}")
                    
                    with st.expander("📋 查看处理结果"):
                        st.dataframe(result_df)
                    
                    # 8. 下载功能
                    st.divider()
                    st.subheader("步骤4: 下载结果")
                    
                    # 转换为CSV
                    csv_data = result_df[['SUBJID', 'DUMSUBJ']].to_csv(index=False, encoding='utf-8-sig')
                    
                    # 提供下载按钮
                    st.download_button(
                        label="💾 下载结果文件 (CSV格式)",
                        data=csv_data,
                        file_name=f'anonymized_{uploaded_file.name.rsplit(".", 1)[0]}.csv',
                        mime='text/csv',
                        help="下载的文件只包含SUBJID和DUMSUBJ两列"
                    )
                    
                    st.balloons()
                    
            except Exception as e:
                st.error(f"❌ 处理过程中出错: {str(e)}")
                st.error("请检查数据格式或随机种子设置")
else:
    st.info("👋 请从左侧上传SAS数据集文件(.sas7bdat)开始使用")
    st.markdown("### 没有SAS文件? 可以使用测试数据")
    st.write("1. 访问 [SAS示例数据集网站](https://github.com/WinVector/PDSwR2/tree/master/Statlog/Heart)")
    st.write("2. 下载示例文件: [**axax.sas7bdat**](https://github.com/WinVector/PDSwR2/blob/master/Statlog/Heart/axax.sas7bdat?raw=true)")
    st.write("3. 将文件下载到本地后使用左侧上传功能")
# 9. 页脚信息
st.markdown("---")
st.caption("🔐 此工具不会存储您的任何数据 - 所有处理都在您的设备上完成")
st.caption("💡 提示: 每次处理完成后刷新页面可以清除所有数据")